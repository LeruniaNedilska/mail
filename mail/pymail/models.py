from bson.objectid import ObjectId


def message(from_user, to_users, subject, date, text, category, important=False, read=False):
    return {"_id": ObjectId(),
            "from": from_user,
            "to": to_users,
            "subject": subject,
            "date": date,
            "text": text,
            "important": important,
            "read": read,
            "type": category
            }


def user_mail(username):
    return {"_id": username,
            "inbox": [],
            "sent": [],
            "trash": [],
            "spam": [],
            "inbox_count": 0,
            "sent_count": 0,
            "trash_count": 0,
            "spam_count": 0
            }
