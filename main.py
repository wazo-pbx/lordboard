# coding=utf-8
from __future__ import unicode_literals
import os.path
import json

import config
from datetime import datetime

from testlink import dao, report
from testlink import setup as setup_testlink
from bottle import route, run, static_file, hook, request

ROOT = os.path.abspath(os.path.dirname(__file__))
STATIC_ROOT = os.path.join(ROOT, "static")

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"


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


@route('/logs')
def log_journal():
    latest = request.query.get('latest', '1') == '1'
    status = request.query.get('status')
    sort = request.query.get('sort', 'timestamp')
    order = request.query.get('order', 'asc')
    timestamp = None
    if 'timestamp' in request.query:
        timestamp = datetime.strptime(request.query['timestamp'], DATETIME_FORMAT)

    logs = dao.log_journal(latest, timestamp, status, sort, order)
    for log in logs:
        log['timestamp'] = log['timestamp'].strftime(DATETIME_FORMAT)

    return {'logs': logs}


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
