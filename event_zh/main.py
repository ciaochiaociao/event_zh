import re
import os
import sys
import logging
import subprocess
import json
import shutil
import glob
import io
from typing import List, Tuple
from lxml import etree
from lxml.etree import Element

from event_zh.utils import logtime
from collections import defaultdict, OrderedDict

debug_logger = setup_logger('debug', 'logs/debug.log', logging.DEBUG)
warning_logger = setup_logger('warning', 'logs/warning.log', logging.WARNING)
info_logger = setup_logger('info', 'logs/info.log', logging.INFO)
info_logger.addHandler(logging.StreamHandler())
error_logger = setup_logger('error', 'logs/error.log', logging.ERROR)
mpath = os.path.dirname(__file__)  # current script directory: .../event_zh/event_zh

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
    "Meet": "Contact",
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


def get_tok_sent(char_b: str, char_e: str, xml_file: str) -> Tuple[Element, Element, Element]:
    """get token and sentence from CoreNLP xml file by char_b and char_e
    >>> token_b, token_e, sentence = get_tok_sent('33', '34', 'test.xml')
    >>> tid_b = token_b.attrib.get('id')
    >>> tid_e = token_e.attrib.get('id')
    >>> sid = sentence.attrib.get('id')
    >>> print(tid_b, tid_e, sid)
    21 21 1
    >>> print(''.join([word.text for word in sentence.iter('word')]))
    新北市新庄区陈姓男子常因细故与邻居争吵，今年8月在家门口遇到隔壁庄姓8旬老翁又发生口角，竟持酒瓶砸向老翁，导致对方跌倒伤及脑部，昏迷数日后中枢神经休克死亡，今天被新北地检署依杀人罪起诉。
    """
    
    with open(xml_file, 'r') as f:
        tree = etree.parse(f)
    
    sentence = tree.xpath(".//token[CharacterOffsetBegin<=" + str(char_b) + " and CharacterOffsetEnd>" + str(char_b) + "]/../..")[0]
    sentence2 = tree.xpath(".//token[CharacterOffsetBegin<" + str(char_e) + " and CharacterOffsetEnd>=" + str(char_e) + "]/../..")[0]
    assert sentence == sentence2, 'char_b {} is in sentence {} and char_e {} is in sentence {}'.format(
        str(char_b), sentence.attrib.get('id'), str(char_e), sentence2.attrib.get('id'))
            
    token_b = tree.xpath(".//token[CharacterOffsetBegin<=" + str(char_b) + " and CharacterOffsetEnd>" + str(char_b) + "]")[0]
    token_e = tree.xpath(".//token[CharacterOffsetBegin<" + str(char_e) + " and CharacterOffsetEnd>=" + str(char_e) + "]")[0]
    
    return token_b, token_e, sentence


def parse_line(line):
    match = re.match(r'(\d+),(\d+) ([\w-]+) (.*)', line)
    try:
        match = [match.group(i) for i in range(0, 5)]
        match[1], match[2] = int(match[1]), int(match[2])
    except AttributeError:
        warning_logger.warn('The input file might not have a correct format, which should be like "59,63 Injure 清理伤口"')
    return match


def bold(text):
    """
    >>> print(bold('Y') + 'N')
    \033[1mY\033[0mN
    """
    return '\033[1m' + text + '\033[0m'


def show_event(s, t, idx_list, d):
    d = list(d)
    if t - s < 20:
        win = 10
    else:
        win = 0
        
    for tok in idx_list:  # make bold ('\033[1m') and red ('\033[91m')
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
        return ''.join(d[s-win:])


@logtime('info')
def read_and_output(fpath, input_folder) -> dict:
    
    fname = os.path.basename(fpath)
    corenlp_xml_path = os.path.join(input_folder, fname + '.xml')
    ee_out_fpath = os.path.join(input_folder, fname + ".arg")

    did = fname

    with open(ee_out_fpath, 'r') as f:
        doc_arg = f.read().splitlines()

    event_list = []
    event = []

    # parse event
    for line in doc_arg:
        if line == "==================":  # start of an event
            if event:
                event_list.append(event)
            event = []
        else:  # lines with the information of event trigger and arguments
            event.append(line)
    
    if event:
        event_list.append(event)

    print('event_list:', event_list)

    event_dict_list = []

    # generate output
    sid_event_count = defaultdict(int)
    
    for evid, event in enumerate(event_list):
        print('event', event)
        l_min, l_max = float('inf'), float('-inf')
        event_dict = OrderedDict({'abs_id': evid, 'trigger': OrderedDict(), 'args': []})

        for idx, arg in enumerate(event):
            _, s, t, type_, cn_word = parse_line(arg)
            if idx == 0:  # trigger
                event_dict['did'] = did
                event_dict['type'] = ace_types[type_]
                event_dict['subtype'] = type_
                event_dict['trigger']['text'] = cn_word
                event_dict['trigger']['char_b'] = s
                event_dict['trigger']['char_e'] = t + 1  # substring: string[s:t] , last word: string[t+1]
                token_b, token_e, sentence = get_tok_sent(s, t + 1, corenlp_xml_path)
                token_b_int, token_e_int = int(token_b.attrib['id']), int(token_e.attrib['id']) + 1
                token_b_int, token_e_int = token_b_int - 1, token_e_int - 1
                event_dict['trigger']['token_b'] = token_b_int
                event_dict['trigger']['token_e'] = token_e_int
                event_dict['trigger']['in_tokens'] = [tok.xpath('word/text()') for tok in token_b.xpath('../token')[token_b_int: token_e_int]]
                event_dict['sid'] = int(sentence.get('id'))
                event_dict['s_text'] = ''.join([word.text for word in sentence.iter('word')])
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
                token_b_int, token_e_int = token_b_int - 1, token_e_int - 1
                arg_dict['token_b'] = token_b_int
                arg_dict['token_e'] = token_e_int
                arg_dict['in_tokens'] = [tok.xpath('word/text()') for tok in token_b.xpath('../token')[token_b_int: token_e_int]]
                event_dict['args'].append(arg_dict)

        print('event_dict', event_dict)
        sid_event_count[event_dict['sid']] += 1
        print('mid', sid_event_count)

        event_dict_list.append(event_dict)

    # sort and add full_id
    output = OrderedDict()
    for i, event_dict in enumerate(event_dict_list):
        # sort
        order = ['id', 'sid', 'did', 'cid', 'type', 'subtype', 's_text', 'trigger', 'args']
        ordered_event_dict = OrderedDict()
        for arg in order:
            if arg in event_dict.keys():
                ordered_event_dict.update({arg: event_dict[arg]})

        fullid = 'D' + str(event_dict['did']) + '-S' + str(event_dict['sid']) + '-EVM' + str(event_dict['id'])
        print(i, fullid)

        # output
        output[fullid] = ordered_event_dict

    print(len(output.items()))
    
    return output


@logtime('info')
def sino_extract(fpath, save_path=None) -> None:
    
    temp_filelist_file = 'default_fpath'
    
    os.environ['SINO_HOME'] = '/workspace/event_zh/event_zh/SinoCoreferencer'
    sino_home = os.environ.get('SINO_HOME')
    
    sino = 'SinoCoreferencer'

    temp_dpath_in_sino = 'data/doc'
    temp_dpath_in_module = os.path.join(sino, temp_dpath_in_sino)
    temp_dir_in_module = os.path.dirname(temp_dpath_in_module)
    cmd = ['bash', 'run.sh', temp_filelist_file]
    
    # --- in project ---
    fname = os.path.basename(fpath)
    wd = os.getcwd()

    # clean old files in sino
    glob_str = temp_dpath_in_module + '.*'
    for f in glob.glob(os.path.join(mpath, glob_str)):
        print('remove', f)
        os.remove(f)
        
    # copy the file to be processed to inside the SinoCoreferencer processing folder
    print(os.path.join(mpath, temp_dir_in_module))
    print(os.getcwd())
    shutil.copy(fpath, os.path.join(mpath, temp_dir_in_module))

    # cd to Sino folder
    os.chdir(sino_home)
    
    try:
        # extract
        pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
                
        stdout, stderr = pipe.communicate(timeout=900)  # if the process is not finished in 15 mins, timeout

        debug_logger.debug(stderr)
        info_logger.info(stdout)
        
        # move output files outside the SinoCoreferencer to the project level
        if save_path is not None:
            shutil.move(temp_dpath_in_sino + '.coref.entities', os.path.join(save_path, fname + '.coref.entities'))
            shutil.move(temp_dpath_in_sino + '.coref.events', os.path.join(save_path, fname + '.coref.events'))
            shutil.move(temp_dpath_in_sino + '.arg', os.path.join(save_path, fname + '.arg'))
            shutil.move(temp_dpath_in_sino + '.xml', os.path.join(save_path, fname + '.xml'))
            shutil.move(temp_dpath_in_sino + '.time', os.path.join(save_path, fname + '.time'))
            shutil.move(temp_dpath_in_sino + '.value', os.path.join(save_path, fname + '.value'))
            shutil.move(temp_dpath_in_sino + '.type', os.path.join(save_path, fname + '.type'))

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
        os.chdir(wd)  # cd back

    return


@logtime('info')
def sino_extract_one(fname, save_path=None, timeout=300) -> None:
    """
    fname: could be absolute path or relative path
    save_path: the folder to save the output files, could also be either relative or absolute
    timeout: timeout value of run SinoCoreferencer in seconds
    """
    os.environ['SINO_HOME'] = '/workspace/event_zh/event_zh/SinoCoreferencer'

    sino_home = os.environ['SINO_HOME']
    print(sino_home)
    fname_abs = os.path.abspath(fname)
    fname_base = os.path.basename(fname_abs)
    save_path = os.path.abspath(save_path)
    print(fname_abs)
    print(fname_base)
    
    wd = os.getcwd()
    
    # cd to Sino folder
    print('cd to SinoCoreferencer folder')
    os.chdir(sino_home)
    
    # clean old files in sino before copying
    glob_str = fname_base + '*'
    for f in glob.glob(glob_str):
        print('remove', f)
        os.remove(f)
        
    # copy the file to be processed to inside the SinoCoreferencer processing folder
    shutil.copy(fname_abs, sino_home)

    # run shell script
    copied_fname_abs = os.path.abspath(fname_base)
    print(fname_abs, 'copied to', copied_fname_abs)
    
    cmd = ['bash', 'run_one.sh', copied_fname_abs]  # actually, run_on.sh could take relative or absolute path

    try:
        # extract
        pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
                
        stdout, stderr = pipe.communicate(timeout=timeout)  # if the process is not finished in 15 mins, timeout

        # logging
        debug_logger.debug(stderr)
        info_logger.info(stdout)
        
        # move output files outside the SinoCoreferencer to the project level
        if save_path is not None:
            if not os.path.exists(save_path):
                os.makedirs(save_path)
            shutil.move(copied_fname_abs + '.coref.entities', os.path.join(save_path, fname_base + '.coref.entities'))
            shutil.move(copied_fname_abs + '.coref.events', os.path.join(save_path, fname_base + '.coref.events'))
            shutil.move(copied_fname_abs + '.arg', os.path.join(save_path, fname_base + '.arg'))
            shutil.move(copied_fname_abs + '.xml', os.path.join(save_path, fname_base + '.xml'))
            shutil.move(copied_fname_abs + '.json', os.path.join(save_path, fname_base + '.json'))
            shutil.move(copied_fname_abs + '.time', os.path.join(save_path, fname_base + '.time'))
            shutil.move(copied_fname_abs + '.value', os.path.join(save_path, fname_base + '.value'))
            shutil.move(copied_fname_abs + '.type', os.path.join(save_path, fname_base + '.type'))
            shutil.move(copied_fname_abs + '.attri', os.path.join(save_path, fname_base + '.attri'))
            shutil.move(copied_fname_abs + '.trigger', os.path.join(save_path, fname_base + '.trigger'))
        else:
            shutil.move(copied_fname_abs + '.coref.entities', fname_abs + '.coref.entities')
            shutil.move(copied_fname_abs + '.coref.events', fname_abs + '.coref.events')
            shutil.move(copied_fname_abs + '.arg', fname_abs + '.arg')
            shutil.move(copied_fname_abs + '.xml', fname_abs + '.xml')
            shutil.move(copied_fname_abs + '.json', fname_abs + '.json')
            shutil.move(copied_fname_abs + '.time', fname_abs + '.time')
            shutil.move(copied_fname_abs + '.value', fname_abs + '.value')
            shutil.move(copied_fname_abs + '.type', fname_abs + '.type')
            shutil.move(copied_fname_abs + '.attri', fname_abs + '.attri')
            shutil.move(copied_fname_abs + '.trigger', fname_abs + '.trigger')

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
        os.chdir(wd)  # cd back

    return


def cckd2fgc(ee_output: dict) -> dict:
    import copy
    result = copy.deepcopy(ee_output)
    
    r = tuple(result.items())
    for fullid, d in r:
        d.pop('id')
#         d.pop('sid')
        d.pop('did')
#         d.pop('s_text')
        
#         # change id
#         def old2newid(oldid):
#             ids = oldid.rsplit('-', 2)
            
#             mid = list(filter(len, re.split(r'(\d+)', ids[-1])))
#             assert len(mid) == 2
#             mid[0] = 'M'
#             mid = ''.join(mid)
            
#             return '-'.join(ids[:-1] + [mid])
        
#         newid = old2newid(fullid)
#         result[newid] = result.pop(fullid)
        
        # remove some trigger keys
        d['trigger'].pop('token_b')
        d['trigger'].pop('token_e')
        d['trigger'].pop('in_tokens')
        d['trigger']['start'] = d['trigger'].pop('char_b')
        d['trigger']['end'] = d['trigger'].pop('char_e')
        
        for arg in d['args']:
            arg.pop('token_b')
            arg.pop('token_e')
            arg.pop('in_tokens')
            arg['start'] = arg.pop('char_b')
            arg['end'] = arg.pop('char_e')
    
    return result
  
# def get_corefs_from_eecoref_and_md(fh_eecoref, fh_md):
#     """
#     >>> with open('data_dir/008.coref.events') as fh_eecoref, \ 
#     ... open('data'):
#         get_corefs_from_eecoref_and_md(fh_eecoref)
#     """
#     corefs_out = OrderedDict()
    
#     # parse coref format
#     try:
#         corefs = parse_coref_format(fh_eecoref)

#     except FileNotFoundError as e:
#         CorefLogger.info(e)
    
#     # get fullid from char_b, char_e
#     md_json = json.load(fh_md) 

#     evid = 0
#     for coref in corefs:
#         if len(coref) > 1:  # only store the coreference chain that has more than two mentions
#             coref_out = []
#             for evm in coref:
#                 fullid = get_fullid_from_char_be(*evm[0], fname, md_json)
#                 if fullid is None:
#                     CorefLogger.warning('Can not get fullid of mentions' + repr(evm) + ' in ' + str(fname) + '.coref.events: Probably *.md.json do not correctly get all mentions in *.arg')
#                     CorefLogger.warning(coref)
#                 else:
#                     coref_out.append(fullid)
#             if len(coref_out) > 1:  # only store the coreference chain that has more than two mentions
#                 corefs_out.update({'D' + str(fname) + '-EV' + str(evid): coref_out})
#                 evid += 1
                
#     return corefs_out


def get_corefs_from_eecoref_and_md(fh_eecoref, fh_md, fname):
    """
    >>> with open('data_dir/008.coref.events') as fh_eecoref, open('data'):
        get_corefs_from_eecoref_and_md(fh_eecoref)
    """
    corefs_out = OrderedDict()
    
    # parse coref format
    try:
        corefs = parse_coref_format(fh_eecoref)

    except FileNotFoundError as e:
        CorefLogger.info(e)
    
    # get fullid from char_b, char_e
    md_json = json.load(fh_md) 

    evid = 0
    for coref in corefs:
        if len(coref) > 1:  # only store the coreference chain that has more than two mentions
            coref_out = []
            for evm in coref:
                fullid = get_fullid_from_char_be(*evm[0], fname, md_json)
                if fullid is None:
                    CorefLogger.warning('Can not get fullid of mentions' + repr(evm) + ' in ' + str(fname) + '.coref.events: Probably *.md.json do not correctly get all mentions in *.arg')
                    CorefLogger.warning(coref)
                else:
                    coref_out.append(fullid)
            if len(coref_out) > 1:  # only store the coreference chain that has more than two mentions
                corefs_out.update({'D' + str(fname) + '-EV' + str(evid): coref_out})
                evid += 1
                
    return corefs_out


def get_fullid_from_char_be(char_b, char_e, did, md_json) -> str:
    """
    >>> md_out_path = 'outputs/' + str(0) + '.md.json'
    >>> with open(md_out_path) as f:
    ...     md_json = json.load(f)
    ...     fullid = get_fullid_from_char_be(42, 43, 0, md_json)
    >>> fullid
    'D0-S1-EVM0'
    """
    # navigate to *.md.json trigger -> char_b, char_e,
    # which is optimized for slicing, so needed to add 1 to match the event extraction package
    try:
        for k, v in md_json.items():
            if 'D' + str(did) in k and v['trigger']['char_b'] == char_b and v['trigger']['char_e'] == char_e + 1:
                return k
    except KeyError:
        for k, v in md_json.items():
            if 'D' + str(did) in k and v['trigger']['start'] == char_b and v['trigger']['end'] == char_e + 1:
                return k


def parse_coref_format(fh) -> List[List[Tuple]]:
    """
    >>> with open('data_dir/001.coref.events') as f:
    >>> corefs = parse_coref_format(f)
    >>> print(corefs)
    [[((345, 345), 'Transport', '入')]]
    """
    COREF_SEP = "============"    
    corefs = []
    coref = []
    for line in fh:
        if line.strip() == COREF_SEP:  # Create a new coref instance
            corefs.append(coref)
            coref = []
        elif line.strip() == "":  # Nothing
            pass
        else:
            data = line.strip().split(' ')
            assert (len(data), len(data[0].split(','))) == (3, 2), (len(data), len(data[0]))
            range_, type_, text = data
            char_b, char_e = range_.split(',')
            
            coref.append([(int(char_b), int(char_e)), type_, text])
            
    return corefs


def extract(fpath, save_path=None, fmt='cckd') -> dict:
    """1. extract event and save to save_path. 2. Also parse to self-defined json format and returns it.
    >>> print(extract('../event_zh/testdoc', '../event_zh/data_dir'))
    """
    
    if save_path is None:
        save_path = os.path.abspath(fpath)
    
    save_path = os.path.abspath(save_path)
    info_logger.info('>>>>> Extracting {}'.format(fpath))
    fpath_full = os.path.abspath(fpath)
    try:
        # sino_extract(fpath, os.path.abspath(save_path))
        sino_extract_one(fpath_full, save_path)
        try:
            print('fpath_full', fpath_full)
            print('save_path', save_path)
            output = read_and_output(fpath_full, save_path)
            info_logger.info('Finished!')
        except KeyError:
            raise
            info_logger.info('{}: No events!'.format(fpath_full))
            output = {}
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        error_logger.error('Skip Event Extraction of this file - {}'.format(fpath))
        output = {}
    except:
        raise
    
    if fmt == 'fgc':
        output = cckd2fgc(output)

    return output


def extract_to_json(fpath: str, save_path=None, fmt='cckd') -> str:
    
    if save_path is None:
        os.path.abspath(fpath)
    
    output = extract(fpath, save_path, fmt)
    with open(os.path.join(save_path, os.path.basename(fpath) + '.md.json'), 'w') as f:
        json.dump(output, f, ensure_ascii=False)
        
    return json.dumps(output, indent=4, ensure_ascii=False)


def extract_and_coref(fname, save_path, fmt='cckd', to_file=False) -> dict:  # TODO: this should be in read_and_output function instead
    """extract events from `fname`, which saves to `save_path` with format `fmt` 
    return 
    >>> extract_and_coref('test2', 'data_dir')
    >>> extract_and_coref('test2', 'data_dir', fmt='fgc', to_json=True)
    """
    fname = os.path.abspath(fname)
    fname_base = os.path.basename(fname)
    save_path = os.path.abspath(save_path)
    ee_md_dict = extract(fname, save_path, fmt=fmt)
    ee_md_dict_dumps = json.dumps(ee_md_dict, ensure_ascii=False)
    
    fh_md = io.StringIO(ee_md_dict_dumps)
    
    # parse corefs format
    try:
        with open(os.path.join(save_path, fname_base + '.coref.events')) as fh_eecoref:
            corefs_dict = get_corefs_from_eecoref_and_md(fh_eecoref, fh_md, fname_base)
    except FileNotFoundError:
        corefs_dict = {}
        raise
        
    result_json = {'events': ee_md_dict, 'corefs': corefs_dict}
    
    if to_file:
        with open(fname + '.ec.json', 'w') as f:
            json.dump(result_json, f, ensure_ascii=False)
    
    return result_json


if __name__ == '__main__':
    
    # test
    # sino_extract_one('../event_zh/testdoc', '../event_zh/data_dir')
    logger.info(extract_and_coref('../event_zh/testdoc', '../event_zh/data_dir', fmt='fgc', to_file=True))
    # logger.info(extract_to_json('../event_zh/testdoc', '../event_zh/data_dir'))
    # logger.info(extract_to_json('../event_zh/testdoc', '../event_zh/data_dir', fmt='fgc'))
