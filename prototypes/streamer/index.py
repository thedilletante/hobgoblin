from json import dumps
from flask import Flask, request

import youtube_dl

app = Flask(__name__)

ydl_opts = {}


# HOW TO:
# start:
# > source venv/bin/activate
# > pip install -r requirements.txt
# > export FLASK_APP=index.py
# > flask run
#
# test:
# > curl -d "url=https://www.youtube.com/watch?v=1gOMilZLIWU" -X POST http://<url>/stream

@app.route('/stream', methods=['POST'])
def stream():
    url = request.form['url']
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return dumps(info)
