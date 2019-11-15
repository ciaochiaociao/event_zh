import sys
from opencc import OpenCC

cc = OpenCC('s2t')
filename = sys.argv[1]
with open(filename, 'r') as f:
    text2conv = [line for line in f]
with open(filename+"_trad", 'w') as f:
    for line in text2conv:
        f.write(cc.convert(line))
