from enum import Enum
from datetime import datetime
from typing import Optional, Any, List
from motor.motor_asyncio import AsyncIOMotorClient
from odmantic import Model, AIOEngine, query
from bson import ObjectId

from .settings import DATABASE_NAME, DATABASE_URL
from .utils import paginated_payload, create_transaction_payload
from .users import User


client = AsyncIOMotorClient(DATABASE_URL)
engine = AIOEngine(motor_client=client, database=DATABASE_NAME)

class TransactionType(str, Enum):
    deposit = "deposit"
    withdrawal = "withdrawal"
    expense = "expense"

class Transaction(Model):
    description: Optional[str]
    amount: Optional[float]
    date: Optional[str]
    timestamp_date: Optional[int]
    type: Optional[TransactionType]
    assigned_id: Optional[str] = None
    completed: Optional[bool] = False
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
        if self.created == 0 or self.created is None:
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
    async def list_all(cls, order_by: Any, start, limit, page_number) -> list:
        transactions = await engine.find(Transaction,skip=start, limit=limit, sort=order_by)
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
    async def get_by_user(cls, order_by: Any, user_id: str, start, limit, page_number):
        transaction = await engine.find(Transaction, Transaction.assigned_id == user_id, skip=start, limit=limit, sort=order_by)
        count = await engine.count(Transaction, Transaction.assigned_id == user_id)
        transaction_list = []
        for one_transaction in transaction:
            payload = await create_transaction_payload(one_transaction)
            transaction_list.append(payload)
        end = start + limit
        total_pages = round(count/limit)
        payload_paginated = await paginated_payload(data=transaction_list, count=count, total_pages=total_pages, end=end, page_number=page_number)
        return payload_paginated


    @classmethod
    async def search(cls, search:str, search_by: str, from_date: int, to_date: int, start, limit, page_number, order_by: Any, user_id: str, current_profile: Any) -> List:
        if search_by == 'date' and bool(from_date) and bool(to_date):
            transactions = await engine.find(Transaction, query.and_(Transaction.created >= from_date, Transaction.created <= to_date), sort=order_by)
            count = await engine.count(Transaction, Transaction.assigned_id == user_id)

        elif search_by == "type" or search_by == "description":
            transactions = await engine.find(Transaction, query.match(Transaction.assigned_id, f".*{search}.*"), sort=order_by, skip=start, limit=limit)
            count = await engine.count(Transaction, Transaction.assigned_id == user_id, f=".*{search}.*")
        
        end = start + limit
        total_pages = round(count/limit)
        payload_paginated = await paginated_payload(data=transactions, count=count, total_pages=total_pages, end=end, page_number=page_number)
        return payload_paginated
