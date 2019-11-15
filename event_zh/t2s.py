import sys
from opencc import OpenCC

cc = OpenCC('t2s')

filename = sys.argv[1]
with open(filename, 'r') as f:
    text2conv = [line for line in f]
print(filename+"_sim")
with open(filename+"_sim", 'w') as f:
    for line in text2conv:
        f.write(cc.convert(line))
