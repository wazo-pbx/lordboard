from __future__ import unicode_literals

import yaml
from datetime import datetime
from testlink import dao


DT_FORMAT = "%Y-%m-%dT%H:%M:%S"


class QuestManager(object):

    def __init__(self, quests):
        self.quests = quests

    def update(self):
        announces = []
        timestamp = datetime.now()
        for quest in self.quests:
            announces.extend(quest.generate_announces(timestamp))
        announces.sort(key=lambda x: x['timestamp'], reverse=True)
        return announces


class Quest(object):

    def __init__(self, dao, message):
        self.dao = dao
        self.message = message

    def make_announce(self, timestamp, message):
        return {'timestamp': timestamp.strftime(DT_FORMAT),
                'category': self.category,
                'announcement': message}


class Leader(Quest):

    category = 'leader'

    def generate_announces(self, timestamp):
        logs = self.dao.all_logs()
        first_log, logs = logs[0], logs[1:]

        scores = self.initial_scores(first_log)

        entries = self.find_people(logs, scores)
        return [self.make_announce(entry[0], self.make_message(entry))
                for entry in entries]

    def initial_scores(self, first_log):
        scores = dict((row['user'], 0) for row in self.dao.all_logs())
        scores[first_log['user']] += 1
        return scores

    def find_people(self, logs, scores):
        last_person = self.find_person(scores)
        for log in logs:
            scores[log['user']] += 1
            person = self.find_person(scores)
            if person is not None and person != last_person:
                yield log['timestamp'], person
                last_person = person

    def find_person(self, scores):
        higest_score = max(scores.values())
        for person, score in scores.iteritems():
            if score == higest_score:
                return person

    def make_message(self, entry):
        return self.message.format('leader', name=entry[1])


class Loser(Leader):

    category = 'loser'

    def find_person(self, scores):
        valid = dict((name, score) for name, score in scores.iteritems() if score > 0)
        if len(valid) >= 2:
            lowest_score = min(valid.values())
            for person, score in valid.iteritems():
                if score == lowest_score:
                    return person

    def make_message(self, entry):
        return self.message.format('loser', name=entry[1])


class TotalLeft(Quest):

    category = 'total_left'

    def generate_announces(self, timestamp):
        total = self.dao.total_manual_tests()
        logs = self.dao.all_logs()
        done = len(logs)
        left = total - done
        if left < self.number:
            log = logs[total - self.number - 1]
            return [self.make_announce(log['timestamp'], self.make_message())]
        return []

    def make_message(self):
        return self.message.format(self.category, number=self.number)


class HundredLeft(TotalLeft):

    number = 100


class FortyTwoLeft(TotalLeft):

    number = 42


class TwentyLeft(TotalLeft):

    number = 20


class TenLeft(TotalLeft):

    number = 10


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
        Loser(dao, message),
        HundredLeft(dao, message),
        FortyTwoLeft(dao, message),
        TwentyLeft(dao, message),
        TenLeft(dao, message),
    )
    quest_manager = QuestManager(quests)
    return quest_manager
