# coding=utf-8
from __future__ import unicode_literals
import os.path
import json

import config
import report
import dao

from bottle import route, run, static_file, hook

STATIC_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "static"))


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


@hook('before_request')
def refresh_build():
    dao.refresh_build()


if __name__ == "__main__":
    run(host=config.HOST, port=config.PORT, reloader=config.DEBUG_RELOAD)
