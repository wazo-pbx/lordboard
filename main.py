# coding=utf-8
import json
import os.path
import psycopg2
import config
from collections import namedtuple

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
    run(host=config.HOST, port=config.PORT)
