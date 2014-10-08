# coding=utf-8
from __future__ import unicode_literals
import os.path
import json
import subprocess

import config
import achievements
from testlink import dao, report
from testlink import setup as setup_testlink
from bottle import route, run, static_file, hook, request

ROOT = os.path.abspath(os.path.dirname(__file__))
STATIC_ROOT = os.path.join(ROOT, "static")

quests = achievements.setup(os.path.join(ROOT, 'messages.yml'))


@route('/report.<output>')
def generate_report(output):
    test_report = dao.manual_test_report()
    return report.generate_report(test_report, output)


@route('/dashboard.json')
def dashboard():
    dashboard = dao.dashboard()
    return json.dumps(dashboard)


@route('/')
def index():
    return static_file('index.html', root=STATIC_ROOT)


@route('/static/<filepath:path>')
def server_static(filepath):
    return static_file(filepath, root=STATIC_ROOT)


@route('/achievements.json')
def list_achievements():
    announces = quests.update()
    timestamp = request.query.get('timestamp', None)
    print "timestamp", timestamp
    if timestamp:
        announces = [a for a in announces if a['timestamp'] > timestamp]
    return json.dumps(announces)


@route('/achievements/<timestamp>.wav')
def generate_audio(timestamp):
    achievements = quests.update()
    entries = [a['announcement']
               for a in achievements
               if a['timestamp'] == timestamp]

    subprocess.check_call(['mkdir', '-p', '/tmp/lordboard'])

    text_filepath = '/tmp/lordboard/{}.txt'.format(timestamp)
    with open(text_filepath, 'w') as f:
        f.write((u" ".join(entries).encode('utf8')))

    filepath = '/tmp/lordboard/{}.wav'.format(timestamp)

    cmd = ['espeak', '-v', 'fr-fr', '-s', '120', '-f', text_filepath, '-w', filepath]
    subprocess.check_call(cmd)

    return static_file('{}.wav'.format(timestamp), root='/tmp/lordboard')


@hook('before_request')
def refresh_build():
    dao.build.refresh()


def setup():
    setup_testlink(host=config.DB_HOST,
                   port=config.DB_PORT,
                   database=config.DB_NAME,
                   user=config.DB_USER,
                   password=config.DB_PASSWORD,
                   project=config.PROJECT_NAME)


if __name__ == "__main__":
    setup()
    run(host=config.HOST, port=config.PORT, reloader=config.DEBUG_RELOAD)
