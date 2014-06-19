# coding=utf-8
from __future__ import unicode_literals
import json
import os.path
import psycopg2
import config
import itertools
import re
from collections import namedtuple
from docutils.core import publish_string
from datetime import datetime

from bottle import route, run, static_file, hook

STATIC_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "static"))

connection = psycopg2.connect(host=config.DB_HOST,
                              port=config.DB_PORT,
                              database=config.DB_NAME,
                              user=config.DB_USER,
                              password=config.DB_PASSWORD)


Build = namedtuple('Build', ['id', 'name'])

build = None


def latest_build():
    query = """
    SELECT
        builds.id,
        builds.name
    FROM
        builds
        INNER JOIN testplans
            ON testplans.id = builds.testplan_id
            INNER JOIN testprojects
                ON testprojects.id = testplans.testproject_id
    WHERE
        testprojects.notes = %(project)s
    ORDER BY
        builds.creation_ts DESC
    LIMIT 1
    """

    cursor = connection.cursor()
    cursor.execute(query, {'project': config.PROJECT_NAME})

    row = cursor.fetchone()
    cursor.close()

    return Build(row[0], row[1])


def total_manual_tests():
    query = """
    SELECT
        count(tcversions.id)
    FROM
        tcversions
        INNER JOIN testplan_tcversions
            ON tcversions.id = testplan_tcversions.tcversion_id
            INNER JOIN builds
                ON builds.testplan_id = testplan_tcversions.testplan_id
    WHERE
        tcversions.execution_type = 1
        AND builds.id = %(build_id)s
    GROUP BY
        builds.id
    """

    cursor = connection.cursor()
    cursor.execute(query, {'build_id': build.id})
    return cursor.fetchone()[0]


def test_statuses():
    query = """
    WITH latest_executions AS
    (
    SELECT
        executions.tcversion_id AS tcversion_id,
        MAX(executions.execution_ts) AS execution_ts
    FROM
        executions
    GROUP BY
        executions.tcversion_id
    )

    SELECT
        (CASE executions.status
         WHEN 'p' THEN 'passed'
         WHEN 'f' THEN 'failed'
         WHEN 'b' THEN 'blocked'
         ELSE executions.status
         END)                       AS status,
        COUNT(executions.status)    AS total
    FROM
        executions
    INNER JOIN latest_executions
        ON executions.tcversion_id = latest_executions.tcversion_id
        AND executions.execution_ts = latest_executions.execution_ts
    INNER JOIN builds
        ON builds.id = executions.build_id
    WHERE
        builds.id = %(build_id)s
        AND executions.execution_type = 1
    GROUP BY
        executions.status
    """

    cursor = connection.cursor()
    cursor.execute(query, {'build_id': build.id})

    statuses = {
        'passed': 0,
        'failed': 0,
        'blocked': 0,
    }

    statuses.update(dict((key, value) for key, value in cursor))
    cursor.close()

    return statuses


def statuses_and_total_executed():
    sums = test_statuses()
    total_executed = sum(sums.values())
    return sums, total_executed


def tests_for_status(status):
    query = """
    WITH latest_executions AS
    (
    SELECT
        executions.tcversion_id         AS tcversion_id,
        MAX(executions.execution_ts)    AS execution_ts
    FROM
        executions
    GROUP BY
        executions.tcversion_id
    )

    SELECT
        tcversions.tc_external_id       AS number,
        parent.name                     AS name,
        executions.notes                AS notes
    FROM
        executions
        INNER JOIN latest_executions
            ON executions.tcversion_id = latest_executions.tcversion_id
            AND executions.execution_ts = latest_executions.execution_ts
        INNER JOIN tcversions
            ON executions.tcversion_id = tcversions.id
            INNER JOIN nodes_hierarchy node
                ON tcversions.id = node.id
                INNER JOIN nodes_hierarchy parent
                    ON node.parent_id = parent.id
        INNER JOIN builds
            ON builds.id = executions.build_id
    WHERE
        builds.id = %(build_id)s
        AND executions.execution_type = 1
        AND executions.status = %(status)s
    ORDER BY
        tcversions.tc_external_id
    """

    cursor = connection.cursor()
    cursor.execute(query, {'build_id': build.id, 'status': status})

    tests = [{
        'name': "X-%s: %s" % (row[0], row[1]),
        'notes': row[2].strip(),
    } for row in cursor]

    cursor.close()

    return tests


def failed_tests():
    return tests_for_status('f')


def blocked_tests():
    return tests_for_status('b')


def executed_per_person():
    query = """
    WITH latest_executions AS
    (
    SELECT
        executions.tcversion_id         AS tcversion_id,
        MAX(executions.execution_ts)    AS execution_ts
    FROM
        executions
    GROUP BY
        executions.tcversion_id
    )

    SELECT
        users.first || ' ' || users.last    AS name,
        (CASE executions.status
         WHEN 'p' THEN 'passed'
         WHEN 'f' THEN 'failed'
         WHEN 'b' THEN 'blocked'
         ELSE executions.status
         END)                               AS status,
        COUNT(executions.id)                AS executed
    FROM
        executions
        INNER JOIN latest_executions
            ON executions.tcversion_id = latest_executions.tcversion_id
            AND executions.execution_ts = latest_executions.execution_ts
        INNER JOIN builds
            ON builds.id = executions.build_id
        INNER JOIN users
            ON executions.tester_id = users.id
    WHERE
        builds.id = %(build_id)s
        AND executions.execution_type = 1
    GROUP BY
        (users.first || ' ' || users.last),
        executions.status
    """

    cursor = connection.cursor()
    cursor.execute(query, {'build_id': build.id})

    scores = {}
    for row in cursor:
        name, status, executed = row
        scores.setdefault(name, {})[status] = executed

    result = [{'name': key, 'executed': value}
              for key, value in scores.iteritems()]

    result.sort(reverse=True, key=lambda x: sum(x['executed'].values()))

    cursor.close()

    return result


def path_for_test(tcversion_id):
    query = """
    WITH RECURSIVE test_path(name, id, parent_id) AS
    (
        SELECT name, id, parent_id FROM nodes_hierarchy WHERE id = (
            SELECT
                parent.parent_id
            FROM
                nodes_hierarchy node
                INNER JOIN nodes_hierarchy parent
                    ON node.parent_id = parent.id
            WHERE
                node.id = %(tcversion_id)s
        )
        UNION ALL
            SELECT
                child.name,
                child.id,
                child.parent_id
            FROM
                test_path
                INNER JOIN nodes_hierarchy child
                    ON test_path.parent_id = child.id
                    AND child.node_type_id = 2
    )
    SELECT name FROM test_path
    """

    cursor = connection.cursor()
    cursor.execute(query, {'tcversion_id': tcversion_id})

    names = [row[0] for row in cursor]
    cursor.close()

    return " / ".join(reversed(names))


def path_per_person():
    query = """
    WITH latest_executed AS
    (
    SELECT
        executions.tester_id            AS tester_id,
        MAX(executions.execution_ts)    AS execution_ts
    FROM
        executions
    GROUP BY
        executions.tester_id
    )

    SELECT
        users.first || ' ' || users.last    AS name,
        executions.tcversion_id             AS tcversion_id
    FROM
        executions
        INNER JOIN latest_executed
            ON executions.tester_id = latest_executed.tester_id
            AND executions.execution_ts = latest_executed.execution_ts
        INNER JOIN builds
            ON builds.id = executions.build_id
        INNER JOIN users
            ON executions.tester_id = users.id
    WHERE
        builds.id = %(build_id)s
        AND executions.execution_type = 1
    GROUP BY
        (users.first || ' ' || users.last),
        executions.tcversion_id
    """

    cursor = connection.cursor()
    cursor.execute(query, {'build_id': build.id})

    results = dict((row[0], path_for_test(row[1])) for row in cursor)
    cursor.close()

    return results


def manual_test_report():
    query = """
    WITH RECURSIVE tree(id, name) AS
    (
        SELECT
            parent.id,
            CAST(parent.name as varchar(200)) as name
        FROM
            nodes_hierarchy parent
        WHERE
            parent.parent_id = (
                SELECT testplans.testproject_id
                FROM builds
                INNER JOIN testplans ON builds.testplan_id = testplans.id
                WHERE builds.id = %(build_id)s
            )
        UNION ALL
        SELECT
            child.id,
            CAST(tree.name || '/' || child.name as varchar(200)) as name
        FROM
            tree
            INNER JOIN nodes_hierarchy child
                ON tree.id = child.parent_id
                AND child.node_type_id = 2
    ),
    latest_executions AS
    (
        SELECT
            executions.tcversion_id AS tcversion_id,
            MAX(executions.execution_ts) AS execution_ts
        FROM
            executions
        GROUP BY
            executions.tcversion_id
    )
    SELECT
        tree.name                           AS folder,
        tcversions.tc_external_id           AS number,
        parent.name                         AS name,
        tcversions.version                  AS version,
        (CASE executions.status
        WHEN 'p' THEN 'passed'
        WHEN 'f' THEN 'failed'
        WHEN 'b' THEN 'blocked'
        ELSE executions.status
        END)                                AS status
    FROM
        executions
        INNER JOIN latest_executions
            ON executions.tcversion_id = latest_executions.tcversion_id
            AND executions.execution_ts = latest_executions.execution_ts
        INNER JOIN builds
            ON builds.id = executions.build_id
        INNER JOIN tcversions
            ON executions.tcversion_id = tcversions.id
            INNER JOIN nodes_hierarchy node
                ON tcversions.id = node.id
                INNER JOIN nodes_hierarchy parent
                    ON node.parent_id = parent.id
                    LEFT OUTER JOIN tree
                        ON parent.parent_id = tree.id
    WHERE
        builds.id = %(build_id)s
        AND executions.execution_type = 1
    ORDER BY
        tree.name ASC,
        parent.node_order DESC
    """

    cursor = connection.cursor()
    cursor.execute(query, {'build_id': build.id})
    report = group_executions_by_folder(cursor)
    cursor.close()

    return report


def group_executions_by_folder(cursor):
    report = []
    key = lambda row: row[0]

    for folder, rows in itertools.groupby(cursor, key):
        executions = tuple({'number': row[1],
                            'name': row[2].decode('utf8'),
                            'version': row[3],
                            'status': row[4].decode('utf8')} for row in rows)
        report.append((folder.decode('utf8'), executions))

    return report


def generate_rst(report):
    lines = []

    title = 'Test report for XiVO {version}'.format(version=build.name)
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
    scores = executed_per_person()
    paths = path_per_person()

    for person in scores:
        person['last_path'] = paths[person['name']]

    return scores


def fetch_stats():
    statuses, total_executed = statuses_and_total_executed()
    stats = {
        'total_manual': total_manual_tests(),
        'total_executed': total_executed,
        'statuses': statuses,
        'lists': {
            'failed': failed_tests(),
            'blocked': blocked_tests(),
        },
        'version': build.name
    }
    connection.commit()

    return stats


def fetch_scoreboard():
    total = total_manual_tests()

    scoreboard = {
        'total': total,
        'rows': scoreboard_rows(),
        'version': build.name
    }
    connection.commit()

    return scoreboard


@route('/report.<output>')
def report_json(output):
    report = manual_test_report()
    if output == 'json':
        return json.dumps(report)
    elif output == 'rst':
        return generate_rst(report)
    markup = generate_rst(report)
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
def fetch_build():
    global build
    build = latest_build()


if __name__ == "__main__":
    run(host=config.HOST, port=config.PORT, reloader=config.DEBUG_RELOAD)
