# coding=utf-8
import json
import os.path
import psycopg2
import config

from bottle import route, run, static_file

XIVO_VERSION = config.XIVO_VERSION

STATIC_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "static"))

connection = psycopg2.connect(host=config.DB_HOST,
                              port=config.DB_PORT,
                              dbname=config.DB_NAME,
                              user=config.DB_USER,
                              password=config.DB_PASSWORD)
connection.autocommit = True


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
        AND builds.name = %(version)s
    GROUP BY
        builds.id
    """

    cursor = connection.cursor()
    cursor.execute(query, {'version': XIVO_VERSION})
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
        builds.name = %(version)s
        AND executions.execution_type = 1
    GROUP BY
        executions.status
    """

    cursor = connection.cursor()
    cursor.execute(query, {'version': XIVO_VERSION})

    statuses = {
        'passed': 0,
        'failed': 0,
        'blocked': 0,
    }

    statuses.update({key: value for key, value in cursor})
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
        builds.name = %(version)s
        AND executions.execution_type = 1
        AND executions.status = %(status)s
    ORDER BY
        tcversions.tc_external_id
    """

    cursor = connection.cursor()
    cursor.execute(query, {'version': XIVO_VERSION, 'status': status})

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


@route('/json')
def data():
    statuses, total_executed = statuses_and_total_executed()
    stats = {
        'total_manual': total_manual_tests(),
        'total_executed': total_executed,
        'statuses': statuses,
        'lists': {
            'failed': failed_tests(),
            'blocked': blocked_tests(),
        },
    }
    return json.dumps(stats)


@route('/')
def index():
    return static_file('index.html', root=STATIC_ROOT)


@route('/static/<filepath:path>')
def server_static(filepath):
    return static_file(filepath, root=STATIC_ROOT)


run(host=config.HOST, port=config.PORT)
