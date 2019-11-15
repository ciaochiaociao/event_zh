import sys
with open(sys.argv[1], "r") as f:
    d = f.read()
print(d)
win = 5 # window size
while True:
    string = input().split()
    s, t = int(string[0]), int(string[1])
    if s < 0 or t >= len(d):
        print("invalid range (should be 0 ~ {})".format(len(d)-1))
    elif s >= win and t < len(d)-win-1:
        print("{} || {}".format(d[s:t+1], d[s-win: t+1+win]))
    elif s < win and t > len(d)-win:
        print("{} || {}".format(d[s:t+1], d))
    elif s < win:
        print("{} || {}".format(d[s:t+1], d[0: t+1+win]))
    else:
        print("{} || {}".format(d[s:t+1], d[s-win: ]))
