import json
import datetime
import time

async def create_transaction_payload(transaction):
    created = transaction.created
    craeted_formated = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(created))
    transaction_payload = {
        "description": transaction.description,
        "amount": transaction.amount,

        "type": transaction.type,
        "date": transaction.date,

        "created": craeted_formated,
        "modified": transaction.modified,
        "id": str(transaction.id)
    }
    return transaction_payload


async def paginated_payload(data, count, total_pages, end, page_number):
    payload = {
        "data": data,
        "next": "",
        "previous": "",
        "total_items": count,
        "total_pages": total_pages
    }
    if end >= count:
        payload["next"] = None

        if page_number > 1:
            payload["previous"] = page_number - 1
        else:
            payload["previous"] = None
    else:
        
        if page_number > 1:
            payload["previous"] = page_number - 1
        else:
            payload["previous"] = None
        payload["next"] = page_number + 1
    return payload


async def open_transaction_file():
    with open("./transaction.json") as f:
        transactions = json.load(f)
        return transactions


async def process_transactions(user, current_user_id, transaction_dict, transaction):
    if (transaction_dict["type"] == "withdrawal" or transaction_dict["type"] == "expense") and (user.balance < transaction_dict["amount"]):
        transaction.completed = False
    elif transaction_dict["type"] != "deposit":
        user.balance -= transaction_dict["amount"]
        transaction.completed = True
    await user.save()
    for i in transaction_dict:
        if i == "id":
            continue
        setattr(transaction, i, transaction_dict[i])
    date_obj = datetime.datetime.strptime(transaction_dict["date"], '%Y-%m-%d')
    timestamp = int(date_obj.timestamp())
    transaction.assigned_id = current_user_id
    transaction.timestamp_date = timestamp
    await transaction.save()
    return transaction
