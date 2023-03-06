import time
from enum import Enum
from datetime import datetime
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorClient
from odmantic import Model, AIOEngine, EmbeddedModel
from bson import ObjectId

from .settings import DATABASE_NAME, DATABASE_URL
from .utils import paginated_payload
from .users import User


client = AsyncIOMotorClient(DATABASE_URL)
engine = AIOEngine(motor_client=client, database=DATABASE_NAME)


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


class TransactionType(str, Enum):
    deposit = "deposit"
    withdrawal = "withdrawal"
    expense = "expense"

class Transaction(Model):
    description: Optional[str]
    amount: Optional[float]
    date: Optional[str]
    type: Optional[TransactionType]
    assigned_id: Optional[str] = None
    created: Optional[int]
    modified: Optional[int]

    async def assigned(self) -> 'Transaction':
        if self.assigned_id:
            user = await User.get(self.assigned_id)
            user = user.dict()
            user['id'] = str(user["id"])
            del user['password']
            return user

    async def save(self):
        self.modified = datetime.utcnow().timestamp()
        if self.created == 0:
            self.created = datetime.utcnow().timestamp()
        await engine.save(self)

    @classmethod
    async def get(cls, id: str) -> 'Transaction':
        transaction = await engine.find_one(Transaction, Transaction.id == ObjectId(id))
        transaction_payload = await create_transaction_payload(transaction)
        return transaction_payload

    async def delete(self):
        await engine.delete(self)

    @classmethod
    async def list_all(cls, start, limit, page_number) -> list:
        transactions = await engine.find(Transaction,skip=start, limit=limit)
        transaction_list = []
        for transaction in transactions:
            _transaction = await create_transaction_payload(transaction)
            transaction_list.append(_transaction)
        count = await engine.count(Transaction)
        end = start + limit
        total_pages = round(count/limit)
        payload_paginated = await paginated_payload(data=transaction_list, count=count, total_pages=total_pages, end=end, page_number=page_number)
        return payload_paginated

    @classmethod
    async def get_by_user(cls, user_id: str, start, limit, page_number):
        transaction = await engine.find(Transaction, Transaction.assigned_id == user_id, skip=start, limit=limit)
        count = await engine.count(Transaction, Transaction.assigned_id == user_id)
        transaction_list = []
        for one_transaction in transaction:
            payload = await create_transaction_payload(one_transaction)
            transaction_list.append(payload)
        end = start + limit
        total_pages = round(count/limit)
        payload_paginated = await paginated_payload(data=transaction_list, count=count, total_pages=total_pages, end=end, page_number=page_number)
        return payload_paginated
