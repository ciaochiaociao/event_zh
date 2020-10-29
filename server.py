#!/usr/bin/python3
from flask import Flask, request
import json
from event_zh.main import extract_and_coref

app = Flask(__name__)


@app.route('/')
def index():
    return "Hello, World!\n"


@app.route('/event', methods=['GET'])
def get_event():
    text = request.args.get('text')
    with open('tempfile', 'w') as f:
        f.write(text)
    result = extract_and_coref('tempfile', 'data_dir', fmt='fgc')
    result = {'text': text, 'result': result}
    return json.dumps(result, ensure_ascii=False)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
