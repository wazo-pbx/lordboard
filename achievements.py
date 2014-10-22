from __future__ import unicode_literals

import yaml
import itertools
from testlink import dao
from datetime import timedelta


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

    def group_by_person(self, logs):
        sorted_logs = sorted(logs, key=lambda x: (x['user'], x['timestamp']))
        grouped_logs = itertools.groupby(sorted_logs, key=lambda x: x['user'])
        return grouped_logs


class Leader(Quest):

    category = 'leader'

    def filter_logs(self):
        logs = self.dao.all_logs()
        if len(logs) > 0:
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


class TestsRemaining(Quest):

    category = 'remaining'

    def filter_logs(self):
        total = self.dao.total_manual_tests()
        logs = self.dao.all_logs()
        done = len(logs)
        left = total - done
        if left <= self.number:
            yield logs[total - self.number - 1]

    def format_message(self, log):
        return self.message.format(self.category, number=self.number)


class HundredRemaining(TestsRemaining):

    number = 100


class FortyTwoRemaining(TestsRemaining):

    number = 42


class TwentyRemaining(TestsRemaining):

    number = 20


class TenRemaining(TestsRemaining):

    number = 10


class TestsFinished(TestsRemaining):

    number = 0
    category = 'finished'


class TestsCompleted(Quest):

    category = 'completed'

    def format_message(self, log):
        return self.message.format(self.category, name=log['user'], number=self.number)

    def filter_logs(self):
        logs_per_person = self.group_by_person(self.dao.all_logs())
        for person, logs in logs_per_person:
            logs = list(logs)
            if len(logs) >= self.number:
                yield logs[self.number - 1]


class FiftyCompleted(TestsCompleted):

    category = '50completed'
    number = 50


class HunderdCompleted(TestsCompleted):

    category = '100completed'
    number = 100


class Regression(Quest):

    category = 'regression'

    def filter_logs(self):
        logs_per_person = self.group_by_person(self.dao.log_journal(status='failed'))
        for person, logs in logs_per_person:
            yield logs.next()

    def format_message(self, log):
        return self.message.format(self.category, name=log['user'])


class Speedy(Quest):

    category = 'speedy'

    def filter_logs(self):
        logs_per_person = self.group_by_person(self.dao.all_logs())
        for person, logs in logs_per_person:
            for log in self.filter_on_timestamp(logs):
                yield log

    def filter_on_timestamp(self, logs):
        logs = list(logs)
        while len(logs) >= self.nb_tests:
            log = logs[0]
            max_time = log['timestamp'] + timedelta(seconds=self.seconds)
            filtered = [l for l in logs
                        if log['timestamp'] <= l['timestamp'] <= max_time]
            if len(filtered) >= self.nb_tests:
                yield filtered[self.nb_tests - 1]
            logs.pop(0)

    def format_message(self, log):
        return self.message.format(self.category, name=log['user'],
                                   number=self.nb_tests,
                                   minutes=self.seconds / 60)


class FiveMinuteSpeedy(Speedy):

    nb_tests = 10
    seconds = 300


class IceBreaker(Quest):

    category = 'icebreaker'

    def filter_logs(self):
        logs = self.dao.all_logs()
        if len(logs) > 0:
            yield logs[0]

    def format_message(self, log):
        return self.message.format(self.category, name=log['user'])


class SingleTest(Quest):

    def filter_logs(self):
        for log in self.dao.all_logs():
            if log['number'] == self.number:
                yield log

    def format_message(self, log):
        return self.message.format(self.category, name=log['user'], number=log['number'])


class ContextSeperation(SingleTest):

    category = 'context_separation'
    number = 235


class Windows(SingleTest):

    category = 'windows'
    number = 125


class Mac(SingleTest):

    category = 'mac'
    number = 124


class Chat(SingleTest):

    category = 'chat'
    number = 155


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
        HundredRemaining(dao, message),
        FortyTwoRemaining(dao, message),
        TwentyRemaining(dao, message),
        TenRemaining(dao, message),
        TestsFinished(dao, message),
        FiftyCompleted(dao, message),
        HunderdCompleted(dao, message),
        Regression(dao, message),
        FiveMinuteSpeedy(dao, message),
        IceBreaker(dao, message),
        ContextSeperation(dao, message),
        Windows(dao, message),
        Mac(dao, message),
        Chat(dao, message),
    )
    quest_manager = QuestManager(quests)
    return quest_manager
