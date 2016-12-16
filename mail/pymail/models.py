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
    return {"username": username,
            "inbox": [],
            "sent": [],
            "trash": [],
            "spam": []
            }
