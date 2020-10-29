import requests

text = '蔡总统抵达位于南部科学工业园区台南园区的台积电晶圆18厂，在厂区大厅短暂发表谈话，随后在台积电董事长刘德音与经济部长沈荣津、行政院政务委员龚明鑫等人陪同进入厂区参访，参访行程未公开。'
URL = 'http://140.109.19.51:5021/event'
method = 'post'  # 'get'

params = {'text': text}
if method.lower() == 'get':
    r = requests.get(url=URL, params=params)
elif method.lower() == 'post':
    r = requests.post(url=URL, data=params)
else:
    raise ValueError

print(r.json())  # return a dictrionary

print(r.text)
