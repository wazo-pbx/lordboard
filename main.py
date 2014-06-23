# coding=utf-8
from __future__ import unicode_literals
import json
import os.path
import config
import re
import itertools
from docutils.core import publish_string
from datetime import datetime

import dao

from bottle import route, run, static_file, hook

STATIC_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "static"))


def generate_rst(report, version):
    lines = []

    title = 'Test report for XiVO {version}'.format(version=version)
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    timestamp = 'Report generated at {date}'.format(date=now)

    lines.extend(_build_title(title, '='))
    lines.append(timestamp)
    lines.append('')
    lines.extend(_build_title('Totals'))
    lines.extend(_build_totals(report))
    lines.append('')
    lines.extend(_build_title('Tests'))

    for folder, executions in report:
        lines.extend(_build_title(folder, '_'))
        lines.extend(_build_table(executions))
        lines.append('')

    markup = '\n'.join(lines)
    return markup


def _build_title(folder, underline='-'):
    yield _escape_markup(folder)
    yield underline * len(folder)
    yield ''


def _build_totals(report):
    totals = {'passed': 0,
              'blocked': 0,
              'failed': 0}

    executions = itertools.chain.from_iterable(x[1] for x in report)
    for execution in executions:
        status = execution['status']
        totals[status] += 1

    for name, count in sorted(totals.iteritems(), key=lambda x: x[0]):
        yield ':{status}: {count}'.format(status=name.capitalize(),
                                          count=count)


def _build_table(executions):
    table_row = "{name} {status}"
    name_template = "X-{e[number]}: {e[name]} (v{e[version]})"

    formatted_names = [_escape_markup(name_template.format(e=e)) for e in executions]
    formatted_statuses = [_escape_markup(e['status'].capitalize()) for e in executions]

    max_name = max(len(n) for n in formatted_names)
    max_status = max(len(s) for s in formatted_statuses)

    title_row = table_row.format(name='Test'.ljust(max_name),
                                 status='Status'.ljust(max_status))
    bar = table_row.format(name='=' * max_name,
                           status='=' * max_status)

    yield bar
    yield title_row
    yield bar

    for name, status in zip(formatted_names, formatted_statuses):
        yield table_row.format(name=name.ljust(max_name),
                               status=status.ljust(max_status))

    yield bar


def _escape_markup(text):
    replace = lambda m: '\\' + m.group(1)
    return re.sub(r'([*`|_])', replace, text)


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
def report_json(output):
    report = dao.manual_test_report()

    if output == 'json':
        return json.dumps(report)
    elif output == 'rst':
        return generate_rst(report, dao.build.version)
    markup = generate_rst(report, dao.build.version)
    return publish_string(markup, writer_name=output,
                          settings_overrides={'input_encoding': 'unicode'})


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
