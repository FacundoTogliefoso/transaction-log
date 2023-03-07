from enum import Enum
from odmantic import Model
from motor.motor_asyncio import AsyncIOMotorClient
from odmantic import AIOEngine
from typing import Optional
from passlib.context import CryptContext
from bson import ObjectId
from pydantic import BaseModel

from .settings import DATABASE_NAME, DATABASE_URL


client = AsyncIOMotorClient(DATABASE_URL)
engine = AIOEngine(motor_client=client, database=DATABASE_NAME)

pwd_context = CryptContext(
        schemes=["pbkdf2_sha256"],
        default="pbkdf2_sha256",
        pbkdf2_sha256__default_rounds=30000
)

def encrypt_password(password):
    return pwd_context.encrypt(password)


def check_encrypted_password(password, hashed):
    return pwd_context.verify(password, hashed)

class Profile(str, Enum):
    admin = "admin"
    client = "client"


class UserLogin(BaseModel):
    username: str
    password: str


class User(Model):
    username: Optional[str]
    email: Optional[str]
    password: Optional[str]
    profile: Optional[Profile]
    balance: Optional[float] = 0

    async def save(self):
        self.password = encrypt_password(self.password)
        await engine.save(self)

    @classmethod
    async def authenticate(cls, user: str, password: str) -> 'User':
        user = await engine.find_one(User, User.username == user)
        if user:
            if check_encrypted_password(password, user.password):
                return user
    
    @classmethod
    async def get(cls, idx: str=None, username: str = None) -> 'User':
        if idx:
            user = await engine.find_one(User, User.id == ObjectId(idx))
        elif username:
            user = await engine.find_one(User, User.username == username)
        return user

    @classmethod
    async def all(cls) -> list:
        users = []
        async for i in engine.find(User,):
            users.append(i)
        return users
    
    async def delete(self):
        await engine.delete(self)
