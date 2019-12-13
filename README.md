# `event_zh`

This package also uses the following paper and its corresponding java source package
SinoCoreferencer: An End-to-End Chinese Event Coreference Resolver
Chen Chen and Vincent Ng
http://www.hlt.utdallas.edu/~yzcchen/coref

# Requirements
python >= 3.5.2 (3.6, 3.7)

# Setup (0.4) (latest)

Setup steps:
1. 
`docker pull ciaochiaociao/cwhsu_event_zh:0.4`
2.
`git clone https://github.com/ciaochiaociao/event_zh`
3.
`docker run -d --rm -v </path/to/repo>:/workspace/event_zh [-e CORENLP_IP=<hostname:port>] -p 5000:5000 -w /workspace/event_zh --name event_zh ciaochiaociao/cwhsu_event_zh:0.4 ./server.py`

## ex0 - Set a corenlp server running in another docker container (default)

Default environment varaible `CORENLP_IP` set to `172.17.0.1`, which is the host ip to access from inside the docker container. Through this, the event extraction inside one container can access the corenlp server running in another docker container on the same host.

```bash
docker run -d --rm -v /d/event_zh:/workspace/event_zh -p 5000:5000 -w /workspace/event_zh --name event_zh ciaochiaociao/cwhsu_event_zh:0.4 ./server.py
```

is the same as

```bash
docker run -d --rm -v /d/event_zh:/workspace/event_zh -e CORENLP_IP=172.17.0.1:9000 -p 5000:5000 -w /workspace/event_zh --name event_zh ciaochiaociao/cwhsu_event_zh:0.4 ./server.py
```

## Ex1 - Set a remote corenlp server

```bash
docker run -d --rm -v /d/event_zh:/workspace/event_zh -e CORENLP_IP=140.109.19.190:9000 -p 5000:5000 -w /workspace/event_zh --name event_zh ciaochiaociao/cwhsu_event_zh:0.4 ./server.py
```

## Test
Run the following in any host
```
import requests


PARAMS = {'text':'蔡总统抵达位于南部科学工业园区台南园区的台积电晶圆18厂，在厂区大厅短暂发表谈话，随后在台积电董事长刘德音与经济部长沈荣津、行政院政务委员龚明鑫等人陪同进入厂区参访，参访行程未公开。'}

URL = 'http://127.0.0.1:5000/event'

r = requests.get(url = URL, params = PARAMS)

print(r.json())  # return a dictrionary

print(r.text)
```

# Setup (0.1) (old version)

## Docker

`docker pull ciaochiaociao/cwhsu_event_zh:0.1`
`docker run -it -v ./event_zh:/workspace/event_zh --name event_zh ciaochiaociao/cwhsu_event_zh:0.1`
`Ctrl + P, Q` to detach from the current container

## `C.UTF-8`
Make sure your environment is `C.UTF-8` (not `en_US.UTF-8`) for the OS support for open chinese documents in python from the following command:
`locale -a`

To change the language settings:
`export LANG=C.UTF-8`

or use the below command to set the langauge  whenever a bash is opened:
`echo "export LANG=C.UTF-8" >> ~/.bashrc`

`python3 fgc_extract.py -i FGC_release_A.json -d test_jsons -o result.json`

## `EE_HOME`
`export EE_HOME=<the path to this github folder>`

## `CORENLP_IP`
`export CORENLP_IP=127.0.0.1:9000`

# Run

## Run in docker container
`docker attach event_zh`
`python3 fgc_extract.py -i input_file -d directory_of_verbose_outputs -o final_output_file`

e.g.

`python3 fgc_extract.py -i FGC_release_A.json -d test_jsons -o result.json`

## Run from oustide the docker container
`docker exec -e LANG=C.UTF-8 -w /event_zh event_zh python3 fgc_extract.py -i FGC_release_A.json -d test_jsons -o result.json`

