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


def scoreboard_rows():
    scores = dao.executed_per_person()
    paths = dao.path_per_person()

    for person in scores:
        person['last_path'] = paths[person['name']]

    return scores


def statuses_and_total_executed():
    sums = dao.test_statuses()
    total_executed = sum(sums.values())
    return sums, total_executed


def fetch_stats():
    statuses, total_executed = statuses_and_total_executed()
    stats = {
        'total_manual': dao.total_manual_tests(),
        'total_executed': total_executed,
        'statuses': statuses,
        'lists': {
            'failed': dao.failed_tests(),
            'blocked': dao.blocked_tests(),
        },
        'version': dao.build.version
    }

    return stats


def fetch_scoreboard():
    total = dao.total_manual_tests()

    scoreboard = {
        'total': total,
        'rows': scoreboard_rows(),
        'version': dao.build.version
    }

    return scoreboard


@route('/report.<output>')
def generate_report(output):
    test_report = dao.manual_test_report()
    return report.generate_report(test_report, output)


@route('/stats.json')
def stats_json():
    stats = fetch_stats()
    return json.dumps(stats)


@route('/scoreboard.json')
def scoreboard_json():
    scoreboard = fetch_scoreboard()
    return json.dumps(scoreboard)


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
