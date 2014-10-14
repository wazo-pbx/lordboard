from __future__ import unicode_literals

import yaml
import itertools
from testlink import dao


DT_FORMAT = "%Y-%m-%dT%H:%M:%S"


class QuestManager(object):

    def __init__(self, quests):
        self.quests = quests

    def announces(self):
        announces = []
        for quest in self.quests:
            announces.extend(quest.announces())
        announces.sort(key=lambda x: x['timestamp'], reverse=True)
        return announces


class Quest(object):

    def __init__(self, dao, message):
        self.dao = dao
        self.message = message

    def announces(self):
        return [self.format_log(log)
                for log in self.filter_logs()]

    def format_log(self, log):
        message = self.format_message(log)
        return self.format_announce(log['timestamp'], message)

    def format_announce(self, timestamp, message):
        return {'timestamp': timestamp.strftime(DT_FORMAT),
                'category': self.category,
                'announcement': message}


class Leader(Quest):

    category = 'leader'

    def filter_logs(self):
        logs = self.dao.all_logs()
        first_log, logs = logs[0], logs[1:]
        scores = self.initial_scores(first_log, logs)
        last_person = self.find_person(scores)

        for log in logs:
            scores[log['user']] += 1
            person = self.find_person(scores)
            if person != last_person:
                yield log
                last_person = person

    def initial_scores(self, first_log, logs):
        scores = dict((row['user'], 0) for row in logs)
        scores[first_log['user']] = 1
        return scores

    def find_person(self, scores):
        higest_score = max(scores.values())
        for person, score in scores.iteritems():
            if score == higest_score:
                return person

    def format_message(self, log):
        return self.message.format('leader', name=log['user'])


class TotalLeft(Quest):

    category = 'total_left'

    def filter_logs(self):
        total = self.dao.total_manual_tests()
        logs = self.dao.all_logs()
        done = len(logs)
        left = total - done
        if left <= self.number:
            yield logs[total - self.number - 1]

    def format_message(self, log):
        return self.message.format(self.category, number=self.number)


class HundredLeft(TotalLeft):

    number = 100


class FortyTwoLeft(TotalLeft):

    number = 42


class TwentyLeft(TotalLeft):

    number = 20


class TenLeft(TotalLeft):

    number = 10


class TestsFinished(TotalLeft):

    number = 0
    category = 'finished'


class TestsPerPerson(Quest):

    category = 'tests_per_person'

    def format_message(self, log):
        return self.message.format(self.category, name=log['user'], number=self.number)

    def filter_logs(self):
        sort_by = lambda x: (x['user'], x['timestamp'])
        all_logs = sorted(self.dao.all_logs(), key=sort_by)

        logs_per_person = itertools.groupby(all_logs, lambda x: x['user'])
        for person, logs in logs_per_person:
            logs = list(logs)
            if len(logs) >= self.number:
                yield logs[self.number - 1]


class FiftyPerPerson(TestsPerPerson):

    number = 50


class HunderdPerPerson(TestsPerPerson):

    number = 100


class Regression(Quest):

    category = 'regression'

    def filter_logs(self):
        logs = self.dao.log_journal(status='failed')
        sorted_logs = sorted(logs, key=lambda x: (x['user'], x['timestamp']))
        grouped_logs = itertools.groupby(sorted_logs, key=lambda x: x['user'])
        for person, logs in grouped_logs:
            yield logs.next()

    def format_message(self, log):
        return self.message.format(self.category, name=log['user'])


class Message(object):

    def __init__(self, filepath):
        with open(filepath) as f:
            self.messages = yaml.load(f)

    def format(self, key, **kwargs):
        tpl = self.messages[key]
        if isinstance(tpl, str):
            tpl = tpl.decode('utf8')
        return tpl.format(**kwargs)


def setup(message_filepath):
    message = Message(message_filepath)
    quests = (
        Leader(dao, message),
        HundredLeft(dao, message),
        FortyTwoLeft(dao, message),
        TwentyLeft(dao, message),
        TenLeft(dao, message),
        TestsFinished(dao, message),
        FiftyPerPerson(dao, message),
        HunderdPerPerson(dao, message),
        Regression(dao, message),
    )
    quest_manager = QuestManager(quests)
    return quest_manager
