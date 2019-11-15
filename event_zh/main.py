import re
import os
import sys
import logging
import subprocess

from event_zh.utils import setup_logger, logtime
from collections import defaultdict

debug_logger = setup_logger('debug', 'debug.log', logging.DEBUG)
warning_logger = setup_logger('warning', 'warning.log', logging.WARNING)
info_logger = setup_logger('info', 'info.log', logging.INFO)
info_logger.addHandler(logging.StreamHandler())
error_logger = setup_logger('error', 'error.log', logging.ERROR)
mpath = os.path.dirname(__file__)

ace_types = {
    "Elect": "Personnel",
    "Declare-Bankruptcy": "Business",
    "Fine": "Justice",
    "Pardon": "Justice",
    "Start-Org": "Business",
    "Execute": "Justice",
    "Convict": "Justice",
    "Transfer-Money": "Transaction",
    "Start-Position": "Personnel",
    "Extradite": "Justice",
    "Transfer-Ownership": "Transaction",
    "Transport": "Movement",
    "Attack": "Conflict",
    "End-Org": "Business",
    "Phone-Write": "Contact",
    "Arrest-Jail": "Justice",
    "Meeting": "Contact",
    "Merge-Org": "Business",
    "Acquit": "Justice",
    "Sue": "Justice",
    "Charge-Indict": "Justice",
    "End-Position": "Personnel",
    "Sentence": "Justice",
    "Die": "Life",
    "Appeal": "Justice",
    "Nominate": "Personnel",
    "Marry": "Life",
    "Trial-Hearing": "Justice",
    "Divorce": "Life",
    "Demonstrate": "Conflict",
    "Be-Born": "Life",
    "Release-Parole": "Justice",
    "Injure": "Life"
}

from typing import Tuple

def get_tok_sent(char_b: str, char_e: str, xml_file: str) -> Tuple['Element', 'Element', 'Element']:
    """get token and sentence from CoreNLP xml file by char_b and char_e
    >>> token_b, token_e, sentence = get_tok_sent(33, 34, 'test.xml')
    >>> tid_b = token_b.attrib.get('id')
    >>> tid_e = token_e.attrib.get('id')
    >>> sid = sentence.attrib.get('id')
    >>> print(tid_b, tid_e, sid)
    21 21 1
    >>> print(''.join([word.text for word in sentence.iter('word')]))
    新北市新庄区陈姓男子常因细故与邻居争吵，今年8月在家门口遇到隔壁庄姓8旬老翁又发生口角，竟持酒瓶砸向老翁，导致对方跌倒伤及脑部，昏迷数日后中枢神经休克死亡，今天被新北地检署依杀人罪起诉。
    """
    
    from lxml import etree
    
    def between():
        pass
    
    with open(xml_file, 'r') as f:
        tree = etree.parse(f)
    
    sentence = tree.xpath(".//token[CharacterOffsetBegin<=" + str(char_b) + " and CharacterOffsetEnd>" + str(char_b) + "]/../..")[0]
    sentence2 = tree.xpath(".//token[CharacterOffsetBegin<" + str(char_e) + " and CharacterOffsetEnd>=" + str(char_e) + "]/../..")[0]
    assert sentence == sentence2, 'char_b {} is in sentence {} and char_e {} is in sentence {}'.format(str(char_b), sentence.attrib.get('id'), str(char_e), sentence2.attrib.get('id') )
            
    token_b = tree.xpath(".//token[CharacterOffsetBegin<=" + str(char_b) + " and CharacterOffsetEnd>" + str(char_b) + "]")[0]
    token_e = tree.xpath(".//token[CharacterOffsetBegin<" + str(char_e) + " and CharacterOffsetEnd>=" + str(char_e) + "]")[0]
    
    return token_b, token_e, sentence


def parse_line(line):
    import re
    match = re.match(r'(\d+),(\d+) ([\w-]+) (.*)', line)
    try:
        match = [ match.group(i) for i in range(0,5) ]
        match[1], match[2] = int(match[1]), int(match[2])
    except AttributeError:
        warning_logger.warn('The input file might not have a correct format, which should be like "59,63 Injure 清理伤口"')
    return match


def bold(text):
    """
    >>> print(bold('Y') + 'N')
    \033[1mY\033[0mN
    """
    return ('\033[1m' + text + '\033[0m')


def show_event(s, t, idx_list, d):
    d = list(d)
    if t - s < 20:
        win = 10
    else:
        win = 0
        
    for tok in idx_list: # make bold ('\033[1m') and red ('\033[91m')
        d[tok[0]] = '\033[91m' + '\033[1m' + d[tok[0]]
        d[tok[1]] = d[tok[1]] + '\033[0m'
    if s < 0 or t >= len(d):
        print("invalid range (should be 0 ~ {})".format(len(d)-1))
    elif s >= win and t < len(d)-win-1:
        return ''.join(d[s-win: t+1+win])
    elif s < win and t > len(d)-win:
        return ''.join(d[s:t+1], d)
    elif s < win:
        return ''.join(d[0: t+1+win])
    else:
        return ''.join(d[s-win: ])


@logtime('info')
def read_and_output(fpath, input_folder) -> dict:
    
    fname = os.path.basename(fpath)
    corenlp_xml_path = os.path.join(input_folder, fname + '.xml')
    ee_out_fpath = os.path.join(input_folder, fname + ".arg")

    did = fname

    with open(ee_out_fpath, 'r') as f:
        doc_arg = f.read().splitlines()
    # print(doc_arg)


    from collections import OrderedDict

    event_list = []
    event = []

    # parse event
    for line in doc_arg:
        if line == "==================":  # start of an event
            if event != []:
                event_list.append(event)
            event = []
        else:  # lines with the information of event trigger and arguments
            event.append(line)
    event_list.append(event)

#     print('event_list:', event_list)

    event_dict_list = []

    # print("=========================")


    # generate output
    lastsid = 0
    id_counter = -1
    sid_event_count = defaultdict(int)
    
    for evid, event in enumerate(event_list):
    #     print(event)
        l_min, l_max = float('inf'), float('-inf')
        idx_list = []
        event_dict = OrderedDict({'abs_id': evid, 'trigger': OrderedDict(), 'args': []})

        for idx, arg in enumerate(event):
            _, s, t, type_, cn_word = parse_line(arg)
#             print('line:', arg)
#             print('parsed:', _, s, t, type_, cn_word)
            if idx == 0:  # trigger
                event_dict['did'] = did
                event_dict['type'] = ace_types[type_]
                event_dict['subtype'] = type_
                event_dict['trigger']['text'] = cn_word
                event_dict['trigger']['char_b'] = s
                event_dict['trigger']['char_e'] = t + 1  # substring: string[s:t] , last word: string[t+1]
                token_b, token_e, sentence = get_tok_sent(s, t + 1, corenlp_xml_path)
                token_b_int, token_e_int = int(token_b.attrib['id']), int(token_e.attrib['id']) + 1
                token_b_int, token_e_int = token_b_int -1, token_e_int - 1
                event_dict['trigger']['token_b'] = token_b_int
                event_dict['trigger']['token_e'] = token_e_int
                event_dict['trigger']['in_tokens'] = [tok.xpath('word/text()') for tok in token_b.xpath('../token')[token_b_int: token_e_int]]
                event_dict['sid'] = int(sentence.get('id'))
                event_dict['s_text'] = ''.join([word.text for word in sentence.iter('word')])

#                 if event_dict['sid'] == lastsid:
#                     id_counter = id_counter + 1
#                 else:
#                     id_counter = 0
#                 lastsid = event_dict['sid']

                id_counter = sid_event_count[event_dict['sid']]

                event_dict['id'] = id_counter

            else:  # argument
                arg_dict = OrderedDict()
                arg_dict['role'] = type_
                arg_dict['text'] = cn_word
                arg_dict['char_b'] = s
                arg_dict['char_e'] = t + 1
                token_b, token_e, _ = get_tok_sent(s, t + 1, corenlp_xml_path)
                token_b_int, token_e_int = int(token_b.attrib['id']), int(token_e.attrib['id']) + 1
                token_b_int, token_e_int = token_b_int -1, token_e_int - 1            
                arg_dict['token_b'] = token_b_int
                arg_dict['token_e'] = token_e_int
                arg_dict['in_tokens'] = [tok.xpath('word/text()') for tok in token_b.xpath('../token')[token_b_int: token_e_int]]
                event_dict['args'].append(arg_dict)

            sid_event_count[event_dict['sid']] += 1
            idx_list.append([s, t])
            l_min = min(l_min, s)
            l_max = max(l_max, t)
    #     print(cc.convert(show_event(l_min, l_max, idx_list, doc)))

        event_dict_list.append(event_dict)
#         print(len(event_dict_list))
    #     print("=========================")


    # sort and add full_id
    output = OrderedDict()
    for i, event_dict in enumerate(event_dict_list):
        # sort
        order = ['id', 'sid', 'did', 'cid', 'type', 'subtype', 's_text', 'trigger', 'args']
        ordered_event_dict = OrderedDict()
        for arg in order:
            if arg in event_dict.keys():
                ordered_event_dict.update({arg: event_dict[arg]})

        # fullid
        import json
#         print(json.dumps(event_dict, indent=4))
        fullid = 'D' + str(event_dict['did']) + '-S' + str(event_dict['sid']) + '-EVM' + str(event_dict['id'])
        print(i, fullid)

        # output
        output[fullid] = ordered_event_dict

    print(len(output.items()))
    
    return output


@logtime('info')
def sino_extract(fpath, save_path=None) -> None:

    from opencc import OpenCC
    import os
    import shutil
    
    fname = os.path.basename(fpath)
    wd = os.getcwd()
#     shutil.copy(fpath, os.path.join(mpath, 'SinoCoreferencer/stanford-corenlp-full-2014-08-27', fname))
    import glob
    for f in glob.glob(os.path.join(mpath, 'SinoCoreferencer/data/doc*')):
        os.remove(f)
    shutil.copy(fpath, os.path.join(mpath, 'SinoCoreferencer/data/doc'))

    os.chdir(os.path.join(mpath, 'SinoCoreferencer'))
    
    try:
        pipe = subprocess.Popen(['bash', 'run.sh', 'test'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
                
        stdout, stderr = pipe.communicate(timeout=900)  # if the process is not finished in 15 mins, timeout

        debug_logger.debug(stderr)
        info_logger.info(stdout)

        if save_path is not None:
            shutil.move('data/doc.coref.entities', os.path.join(save_path, fname + '.coref.entities'))
            shutil.move('data/doc.coref.events', os.path.join(save_path, fname + '.coref.events'))
            shutil.move('data/doc.arg', os.path.join(save_path, fname + '.arg'))
            shutil.move('data/doc.xml', os.path.join(save_path, fname + '.xml'))
            shutil.move('data/doc.time', os.path.join(save_path, fname + '.time'))
            shutil.move('data/doc.value', os.path.join(save_path, fname + '.value'))
            shutil.move('data/doc.type', os.path.join(save_path, fname + '.type'))

    except subprocess.CalledProcessError:
        error_logger.error('Event Extraction Failed - file {}'.format(fname))
        raise
    except subprocess.TimeoutExpired:
        error_logger.error('Event Extraction Timeout Expired (over 15 mins) - file {}'.format(fname))
        raise
    except:
        error_logger.error('Other Exception in Event Extraction raised - file {} [{} - {}]'.format(fname, sys.exc_info()[0], sys.exc_info()[1]))
        raise
    finally:
        os.chdir(wd)

    return

def extract(fpath, save_path=None) -> dict:
    info_logger.info('>>>>> Extracting {}'.format(fpath))
    fpath_full = os.path.abspath(fpath)
    try:
        sino_extract(fpath, os.path.abspath(save_path))
        try:
            output = read_and_output(fpath_full, save_path)
            info_logger.info('Finished!')
        except KeyError:
            info_logger.info('{}: No events!'.format(fpath_full))
            output = {}
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        error_logger.error('Skip Event Extraction of this file - {}'.format(fpath))
        output = {}
    except:
        raise
        
    return output


def extract_to_json(fpath: str, save_path) -> None:
    
    output = extract(fpath, save_path)
    
    import json
    import os
#     print(json.dumps(event_dict_list, indent=4, ensure_ascii=False))
#     print(json.dumps(output, indent=4, ensure_ascii=False))
    with open(os.path.join(save_path, os.path.basename(fpath) + '.md.json'), 'w') as f:
        json.dump(output, f)
        
    return output