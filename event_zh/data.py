from pathlib import Path
from typing import List, Union

import requests

URL = 'http://140.109.19.51:5021'
METHOD = 'post'


class EventPipeline:

    def __init__(self, url=URL, method=METHOD):
        self.url = url
        self.method = method

    def annotate(self, input: Union[str, List[str]], is_path=False, is_dir=False) -> Union[dict, List[dict]]:
        """Annotate from text, a list of text, or from a file path, a list of file paths

        Returns:
            `dict` or `List[dict]`
        Examples::
            pipeline.annotate('document text')
            pipeline.annotate(['document1 text', 'document2 text'])

            pipeline.annotate('path/to/file', is_path=True)
            pipeline.annotate(['path/to/file1', 'path/to/file2'], is_path=True)

            pipeline.annotate('path/to/directory/of/files', is_dir=True)
        """

        if isinstance(input, str):  # document content
            if is_dir:
                return self.annotate_from_dir(input)
            else:
                if is_path:
                    return self.annotate_from_filepath(input)
                else:
                    return self.annotate_from_text(input)
        elif isinstance(input, list):  # list of file paths
            if is_dir:
                raise ValueError('Extracting from list of directories is not supported')
            else:
                if is_path:
                    return self.annotate_from_filepaths(input)
                else:
                    return self.annotate_from_texts(input)
        else:
            raise ValueError(str(type(input)) + ' is not supported.')

    def annotate_from_text(self, text: str) -> dict:
        params = {'text': text}
        if self.method.lower() == 'get':
            r = requests.get(url=self.url + '/event', params=params)
        elif self.method.lower() == 'post':
            r = requests.post(url=self.url + '/event', data=params)
        else:
            raise ValueError

        return r.json()

    def annotate_from_filepath(self, filepath: str) -> dict:
        with Path(filepath).open(mode='r') as f:
            text = f.read()
        return self.annotate_from_text(text)

    def annotate_from_texts(self, texts) -> List[dict]:
        return [self.annotate_from_text(text) for text in texts]

    def annotate_from_filepaths(self, filepaths: List[str]) -> List[dict]:
        return [self.annotate_from_filepath(filepath) for filepath in filepaths]

    def annotate_from_dir(self, input_dir: str) -> List[dict]:
        input_dir = Path(input_dir)
        assert input_dir.is_dir()
        filepaths = [str(f) for f in input_dir.iterdir()]

        return [self.annotate_from_filepath(filepath) for filepath in filepaths]


if __name__ == '__main__':

    # usage example 1: single document
    text = '蔡总统抵达位于南部科学工业园区台南园区的台积电晶圆18厂，在厂区大厅短暂发表谈话，随后在台积电董事长刘德音与经济部长沈荣津、行政院政务委员龚明鑫等人陪同进入厂区参访，参访行程未公开。'
    event_pipeline = EventPipeline('http://140.109.19.51:5011', method='post')
    print(event_pipeline.annotate(text))

    # usage example 2: single document (file path)
    print(event_pipeline.annotate('path/to/file', is_path=True))

    # usage example 3: multiple documents (list of texts)
    file_list = ['這是文件1的範例內容。', '這是文件2的範例內容。', '這是文件3的範例內容。']
    print(event_pipeline.annotate(file_list))

    # usage example 4: multiple documents (list of file paths)
    file_list = ['data/1', 'data/2', 'data/3']
    print(event_pipeline.annotate(file_list, is_path=True))

    # usage example 5: multiple documents (from a directory that stores all documents to be processed)
    input_dir = 'data'
    print(event_pipeline.annotate(input_dir, is_dir=True))

