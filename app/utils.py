import json


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
