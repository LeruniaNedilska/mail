from pymail.models import *
from pymongo import MongoClient
from bson.objectid import ObjectId
from operator import itemgetter
import redis
from bson.json_util import dumps, loads
from datetime import datetime, timedelta


class DB:
    def __init__(self):
        self.client = MongoClient()
        self.db = self.client.pymail
        self.mail = self.db.mail
        self.users = redis.StrictRedis(decode_responses=True, db=0)
        self.stat = redis.StrictRedis(decode_responses=True, db=1)
        self.users.flushall()
        self.stat.flushall()

    def add_user(self, username):
        self.mail.insert_one(user_mail(username))

    def remove_user(self, username):
        self.mail.remove({"_id": username})

    def add_message(self, from_user, to_users, subject, date, text, category, user, important=False, read=True):
        self.mail.update_one({"_id": user},
                             {"$addToSet": {category: message(from_user, to_users, subject,
                                            date, text, category, important, read)}})
        self.mail.update_one({"_id": user},
                             {"$inc": {category+"_count": 1}})
        self.users.hset(user, category+'_changed', 1)
        self.stat.hset(user, 'stat_changed', 1)

    def send_registration_message(self, user, date):
        mess = "We are glad to see you registered!\n\n" \
               "Keep in touch!\n\n" \
               "Best regards,\n" \
               "Pymail administration."
        self.add_message('admin', [user], 'Welcome to pymail!', date, mess, 'inbox', user, read=False)
        self.add_message('admin', [user], 'Welcome to pymail!', date, mess, 'sent', 'admin')

    def copy_message(self, from_user, to_users, subject, date, text, category, read, important, user, new_category):
        self.mail.update_one({"_id": user},
                             {"$addToSet": {new_category: message(from_user, to_users, subject,
                                            date, text, category, important, read)}})
        self.mail.update_one({"_id": user},
                             {"$inc": {new_category+'_count': 1}})
        self.stat.hset(from_user, 'stat_changed', 1)
        self.users.hset(user, new_category+'_changed', 1)

    def remove_message(self, category, user, message_id):
        self.mail.update_one({"_id": user},
                             {"$pull": {category: {"_id": ObjectId(message_id)}}})
        self.mail.update_one({"_id": user},
                             {"$inc": {category+"_count": -1}})
        self.users.hset(user, category+"_changed", 1)
        self.stat.hset(user, 'stat_changed', 1)

    def get_category(self, username, category):
        if self.mail.find_one({"_id": username, category+'_count': {"$gte": 100}}):
            if self.users.exists(username) == 1 and self.users.hget(username, category+'_changed') == '0' \
                    and self.users.hexists(username, category) == 1:
                result = loads(self.users.hget(username, category))
                month = str(datetime.now().month)
                self.stat.hincrby(username, 'cachehits_'+month)
                msg = "Results extracted from cache."
            else:
                result = sorted(self.mail.find_one({"_id": username}, {category: "1"})[category],
                                key=itemgetter('date'), reverse=True)
                r = result
                self.users.hmset(username, {category: dumps(r), category+"_changed": 0})
                msg = "Results extracted from database."
        else:
            result = sorted(self.mail.find_one({"_id": username}, {category: "1"})[category], key=itemgetter('date'),
                            reverse=True)
            msg = "Results extracted from database."
            self.stat.hincrby(username, 'dbhits_' + str(datetime.now().month))
        return result, msg

    def find_message_category(self, user, message_id):
        category = ['inbox', 'sent', 'trash', 'spam']
        for c in category:
            if self.mail.find_one({"_id": user, c+"._id": ObjectId(message_id)}):
                return c

    def find_message_by_id(self, user, category, message_id):
        return list(self.mail.aggregate([
                {"$match": {"_id": user}},
                {"$unwind": "$"+category},
                {"$match": {category+"._id": ObjectId(message_id)}},
                {"$group": {"_id": '$_id', category: {"$push": "$"+category}}}
            ]))[0][category][0]

    def mark_message_important(self, user, message_id, mark, category=None):
        if category is None:
            category = self.find_message_category(user, message_id)
        self.mail.update_one({"_id": user, category+"._id": ObjectId(message_id)},
                             {"$set": {category+".$.important": mark}})
        self.users.hset(user, 'important_changed', 1)

    def mark_message_read(self, user, message_id, mark):
        self.mail.update_one({"_id": user, "inbox._id": ObjectId(message_id)},
                             {"$set": {"inbox.$.read": mark}})

    def move_message(self, user, from_category, message_id, to_category=None):
        mess = self.find_message_by_id(user, from_category, message_id)
        if to_category is None:
            to_category = mess['type']
        self.copy_message(mess['from'], mess['to'], mess['subject'], mess['date'],
                          mess['text'], mess['type'], mess['read'], mess['important'], user, to_category)
        self.remove_message(from_category, user, message_id)

    def find_important_messages(self, user):
        if self.users.hget(user, 'important_changed') == '0':
            msg = "Results extracted from cache."
            self.stat.hincrby(user, 'cachehits_' + str(datetime.now().month))
            return loads(self.users.hget(user, "important")), msg
        important = []
        category = ['inbox', 'sent', 'trash', 'spam']
        for c in category:
            record = self.mail.aggregate([
                {"$match": {"_id": user}},
                {"$unwind": "$"+c},
                {"$match": {c+".important": True}},
                {"$group": {"_id": '$'+c, "important": {"$push": "$"+c}}}
            ])
            if record:
                for r in record:
                    important.append(r['important'][0])
        i = important
        msg = "Results extracted from database."
        self.stat.hincrby(user, 'dbhits_' + str(datetime.now().month))
        self.users.hmset(user, {'important': dumps(i), 'important_changed': 0})
        return important, msg

    def new_message_amount(self, user):
        cursor = self.mail.aggregate([
            {"$match": {"_id": user}},
            {"$unwind": "$inbox"},
            {"$match": {"inbox.read": False}},
            {"$group": {"_id": '$_id', "count": {"$sum": 1}}}
        ])
        for cur in cursor:
            return int(cur['count'])
        else:
            return 0

    def important_messages_amount(self, user):
        count = 0
        category = ['inbox', 'sent', 'trash', 'spam']
        for c in category:
            cursor = self.mail.aggregate([
                {"$match": {"_id": user}},
                {"$unwind": "$"+c},
                {"$match": {c+".important": True}},
                {"$group": {"_id": '$_id', "count": {"$sum": 1}}}
            ])
            for cur in cursor:
                count += int(cur['count'])
        return count

    def message_amount(self, user):
        pipeline = [
            {"$match": {"_id": user}},
            {"$project": {
                "sentNumber": {"$size": "$sent"},
                "trashNumber": {"$size": "$trash"},
                "spamNumber": {"$size": "$spam"}}}
        ]
        return list(self.mail.aggregate(pipeline))[0]

    def find_message_by_text(self, user, category, text):
        fields = ['.from', '.to', '.subject', '.text', '.date']
        result = {}
        for f in fields:
            record = self.mail.aggregate([
                {"$match": {"_id": user}},
                {"$unwind": "$" + category},
                {"$match": {category+f: {"$regex": ".*"+text+".*"}}},
                {"$group": {"_id": '$_id', "important": {"$push": "$" + category}}}
            ])
            if record:
                for r in record:
                    for mess in r['important']:
                        result[mess['_id']] = mess
        return list(result.values())

    def find_important_message_by_text(self, user, text):
        inbox = self.find_message_by_text(user, 'inbox', text)
        sent = self.find_message_by_text(user, 'sent', text)
        trash = self.find_message_by_text(user, 'trash', text)
        spam = self.find_message_by_text(user, 'spam', text)
        all = inbox + sent + trash + spam
        important = [im for im in all if im['important'] is True]
        return important

    def spam_stats(self, date):
        record = self.mail.aggregate([
            {"$unwind": "$spam"},
            {"$match": {"spam.date": {"$regex": ".*" + date + ".*"}}},
            {"$group": {"_id": '$spam.from', "spam": {"$sum": 1}}}
        ])
        return list(record)

    def user_stats(self, date, user, category):
        record = self.mail.aggregate([
            {"$match": {"_id": user}},
            {"$unwind": "$"+category},
            {"$match": {category+".date": {"$regex": ".*" + date + ".*"}}},
            {"$group": {"_id": '$_id', category: {"$sum": 1}}}
        ])
        for r in record:
            return r
        return {'_id': user, category: 0}

    def stats(self, date):
        result = {}
        spam = self.spam_stats(date)
        for user in self.mail.find():
            if self.stat.hexists(user['_id'], date) == 1 and self.stat.hget(user['_id'], 'stat_changed') == '0':
                result[user['_id']] = loads(self.stat.hget(user['_id'], date))
            else:
                inbox = self.user_stats(date, user['_id'], 'inbox')
                sent = self.user_stats(date, user['_id'], 'sent')
                for s in spam:
                    print(s['_id'])
                    if s['_id'] == user['_id']:
                        result[user['_id']] = {'inbox': inbox['inbox'], 'sent': sent['sent'], 'spam': s['spam']}
                        break
                else:
                    result[user['_id']] = {'inbox': inbox['inbox'], 'sent': sent['sent'], 'spam': 0}
                res = result[user['_id']]
                self.stat.hmset(user['_id'], {date: dumps(res), 'stat_changed': '0'})
        return result

    def clear_old(self, user, month):
        for key in self.stat.hkeys(user):
            part = key.split('_')[0]
            if part == 'cachehits' or part == 'dbhits':
                mon = key.split('_')[1]
                if mon != month:
                    self.stat.hdel(user, key)
            elif part != 'stat' and part != 'dbmemory':
                now = datetime.now()
                ago = now - timedelta(days=30)
                if not ago <= datetime.strptime(key, "%Y-%m-%d") <= now:
                    self.stat.hdel(user, key)

    def memory_usage(self, user):
        month = str(datetime.now().month)
        self.clear_old(user, month)
        result = {}
        if self.stat.hexists(user, 'cachehits_'+month):
            result['cachehits'] = self.stat.hget(user, 'cachehits_'+month)
        else:
            result['cachehits'] = '0'
            self.stat.hset(user, 'cachehits_'+month, 0)
        if self.stat.hexists(user, 'dbhits_'+month):
            result['dbhits'] = self.stat.hget(user, 'dbhits_'+month)
        else:
            result['dbhits'] = '0'
            self.stat.hset(user, 'dbhits_'+month, 0)
        return result

