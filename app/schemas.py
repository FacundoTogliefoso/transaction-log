from datetime import datetime
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorClient
from odmantic import Model, AIOEngine, EmbeddedModel
from bson import ObjectId
import time
from settings import DATABASE_NAME, DATABASE_URL
from utils import paginated_payload


client = AsyncIOMotorClient(DATABASE_URL)
engine = AIOEngine(motor_client=client, database=DATABASE_NAME)


async def create_client_payload(client):
    created = client.created
    craeted_formated = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(created))
    client_payload = {
        "name": client.name,
        "lastname": client.lastname,
        "balance": client.balance,

        "transactions": client.transactions,
        "expenses": client.expenses,

        "created": craeted_formated,
        "modified": client.modified,
        "id": str(client.id)
    }
    return client_payload


# Expenses - Withdrawals - Deposits
class Transactions(EmbeddedModel):
    title: Optional[str]
    text: Optional[str]
    type: Optional[str]
    cost: Optional[str]
    created: Optional[int]
    modified: Optional[int]


class Expenses(EmbeddedModel):
    title: Optional[str]
    text: Optional[str]
    cost: Optional[str]
    created: Optional[int]
    modified: Optional[int]


class Client(Model):
    name: Optional[str]
    lastname: Optional[str]
    transactions: Optional[List[Transactions]]
    balance: Optional[int]
    expenses: Optional[Expenses]
    created: Optional[int]
    modified: Optional[int]

    async def save(self):
        self.modified = datetime.utcnow().timestamp()
        if self.created == 0:
            self.created = datetime.utcnow().timestamp()
        await engine.save(self)

    @classmethod
    async def get(cls, id: str) -> 'Client':
        client = await engine.find_one(Client, Client.id == ObjectId(id))
        client_payload = await create_client_payload(client)
        return client_payload

    @classmethod
    async def get_without_subjects_career(cls, id: str) -> 'Client':
        client = await engine.find_one(Client, Client.id == ObjectId(id))
        return client

    async def delete(self):
        await engine.delete(self)

    @classmethod
    async def list_all(cls, start, limit, page_number) -> list:
        clients = await engine.find(Client,skip=start, limit=limit)
        client_list = []
        for client in clients:
            _client = await create_client_payload(client)
            client_list.append(_client)
        count = await engine.count(Client)
        end = start + limit
        total_pages = round(count/limit)
        payload_paginated = await paginated_payload(data=client_list, count=count, total_pages=total_pages, end=end, page_number=page_number)
        return payload_paginated
