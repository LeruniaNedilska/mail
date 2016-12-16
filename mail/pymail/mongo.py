from pymail.models import *
from pymongo import MongoClient
from bson.objectid import ObjectId
from operator import itemgetter


class DB:
    def __init__(self):
        self.client = MongoClient()
        self.db = self.client.pymail
        self.mail = self.db.mail

    def add_user(self, username):
        self.mail.insert_one(user_mail(username))

    def find_users_messages(self, username, category):
        return sorted(self.mail.find_one({"username": username}, {category: "1"})[category], key=itemgetter('date'),
                      reverse=True)

    def add_message(self, from_user, to_users, subject, date, text, category, user):
        self.mail.update_one({"username": user},
                             {"$addToSet": {category: message(from_user, to_users, subject,
                                            date, text, category)}})

    def copy_message(self, from_user, to_users, subject, date, text, category, read, important, user, new_category):
        self.mail.update_one({"username": user},
                             {"$addToSet": {new_category: message(from_user, to_users, subject,
                                            date, text, category, important, read)}})

    def remove_message(self, category, user, message_id):
        self.mail.update_one({"username": user},
                             {"$pull": {category: {"_id": ObjectId(message_id)}}})

    def find_message_category(self, user, message_id):
        if self.mail.find_one({"username": user, "inbox._id": ObjectId(message_id)}):
            return "inbox"
        elif self.mail.find_one({"username": user, "sent._id": ObjectId(message_id)}):
            return "sent"
        elif self.mail.find_one({"username": user, "trash._id": ObjectId(message_id)}):
            return "trash"
        elif self.mail.find_one({"username": user, "spam._id": ObjectId(message_id)}):
            return "spam"

    def mark_message_important(self, user, message_id, mark, category=None):
        if category is None:
            category = self.find_message_category(user, message_id)
        self.mail.update_one({"username": user, category+"._id": ObjectId(message_id)},
                             {"$set": {category+".$.important": mark}})

    def mark_message_read(self, user, message_id, mark):
        self.mail.update_one({"username": user, "inbox._id": ObjectId(message_id)},
                             {"$set": {"inbox.$.read": mark}})

    def move_message(self, user, from_category, message_id, to_category=None):
        mail = self.mail.find_one({"username": user}, {from_category: "1"})
        for mess in mail[from_category]:
            if mess['_id'] == ObjectId(message_id):
                print("We got here")
                if to_category is None:
                    to_category = mess['type']
                self.copy_message(mess['from'], mess['to'], mess['subject'], mess['date'],
                                  mess['text'], mess['type'], mess['read'], mess['important'], user, to_category)
                self.remove_message(from_category, user, message_id)
                break

    def new_message_amount(self, user):
        message_list = self.find_users_messages(user, "inbox")
        return len([m for m in message_list if m['read'] is False])

    def find_important_messages(self, user):
        all_messages = self.find_users_messages(user, "inbox") + \
                       self.find_users_messages(user, "sent") + \
                       self.find_users_messages(user, "trash") + \
                       self.find_users_messages(user, "spam")
        return [m for m in all_messages if m['important'] is True]

    def important_messages_amount(self, user):
        return len(self.find_important_messages(user))

    def message_amount(self, user):
        pipeline = [
            {"$match": {"username": user}},
            {"$project": {
                "sentNumber": {"$size": "$sent"},
                "trashNumber": {"$size": "$trash"},
                "spamNumber": {"$size": "$spam"}}}
        ]
        return list(self.mail.aggregate(pipeline))[0]
