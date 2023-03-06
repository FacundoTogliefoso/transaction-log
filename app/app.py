import redis
import json

from typing import List
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse, Response
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException
from fastapi.middleware.cors import CORSMiddleware

# from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter
# from prometheus_fastapi_instrumentator import Instrumentator

from .users import User, UserLogin, Profile, encrypt_password
from .schemas import Transaction
from .settings import JWT_EXPIRE, ADMIN_PASSWORD, ADMIN_USERNAME, Settings
from .utils import open_transaction_file


app = FastAPI()

rd = redis.Redis(host='redis', port=6379, db=0, charset="utf-8", decode_responses=True)

# transaction_create = Counter('transaction_create_total', 'Total Transaction created', ['method', 'endpoint'])

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instrumentator().instrument(app).expose(app)

@AuthJWT.load_config
def get_config():
    return Settings()

@app.exception_handler(AuthJWTException)
def authjwt_exception_handler(request: Request, exc: AuthJWTException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )

@app.post('/login')
async def login(login_form: UserLogin, Authorize: AuthJWT = Depends()):
    user = await User.authenticate(login_form.username, login_form.password)
    if not user:
        raise HTTPException(status_code=401,detail="Bad username or password")
    access_token = Authorize.create_access_token(subject=user.username, user_claims={'profile': user.profile, "user_id": str(user.id), "name": user.username}, fresh=True)
    refresh_token = Authorize.create_refresh_token(subject=user.username, user_claims={'profile': user.profile, "user_id": str(user.id), "name": user.username})
    return {"access_token": access_token, "refresh_token": refresh_token, "expire": JWT_EXPIRE}

@app.post('/refresh')
def refresh(Authorize: AuthJWT = Depends()):
    Authorize.jwt_refresh_token_required()
    current_user = Authorize.get_jwt_subject()
    new_access_token = Authorize.create_access_token(subject=current_user, user_claims={'profile': current_user.profile},fresh=False)
    return {"access_token": new_access_token, "expire": JWT_EXPIRE}

@app.get('/users/create-superuser', response_description="Create superuser")
async def create_superuser():
    u = await User.get(username=ADMIN_USERNAME)
    if not u:
        u = User(
            username = ADMIN_USERNAME,
            password = ADMIN_PASSWORD,
            profile = Profile.admin
        )
        await u.save()    
    return {}

@app.post('/users', response_description="Create user", response_model=User)
async def create_user(user: User, Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()
    u = await User.get(username = user.username)
    if not u:
        await user.save()
        return user
    raise HTTPException(status_code=401, detail=f"Username {user.username} already exists. Please use another one.")

@app.get('/users', response_description="list users", response_model=List[User])
async def list_users(Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()
    current_profile = Authorize.get_raw_jwt().get('profile')
    if current_profile == Profile.admin:
        users = await User.all()
        return users
    raise HTTPException(status_code=401, detail="You don´t have permissions to do this action.")

@app.get("/users/{user_id}", response_description="show a single user", response_model=User)
async def show_user(user_id: str, Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()
    user = await User.get(user_id)
    if user is not None:
        return user
    raise HTTPException(status_code=404, detail=f"Tag {user_id} not found")

@app.put("/users/{user_id}", response_description="update a single user", response_model=User)
async def update_user(user_id: str, user_up: User, Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()
    current_profile = Authorize.get_raw_jwt().get('profile')
    if current_profile == Profile.admin:
        user = await User.get(user_id)
        if user is not None:
            data = user_up.dict(exclude_unset=True)
            for i in data:
                if i == 'id':
                    continue
                setattr(user,i, data[i])
            await user.save()
            return user
        raise HTTPException(status_code=404, detail=f"Tag {user_id} not found")
    else:
        raise HTTPException(status_code=401, detail="You don´t have permissions to do this action.")
    
@app.delete("/users/{user_id}", response_description="delete a single user", operation_id="authorize")
async def delete_user(user_id: str, Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()
    current_profile = Authorize.get_raw_jwt().get('profile') 
    if current_profile == Profile.admin:
        user = await User.get(user_id)
        if user is not None:
            await user.delete()
            return True
        raise HTTPException(status_code=404, detail=f"Tag {user_id} not found")
    raise HTTPException(status_code=401, detail=f"You dont have permissions to do this action.")

#################################

@app.post("/transactions", response_description="Create a transaction.", response_model=Transaction)
async def upload_transactions(Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()

    transactions_list = await open_transaction_file()

    current_user_id = Authorize.get_raw_jwt().get('user_id')
    user = await User.get(idx=current_user_id)
    user.balance += sum(t["amount"] for t in transactions_list if t["type"] == "deposit")
    await user.save()
    for transaction_dict in transactions_list:
        if transaction_dict["type"] == "withdrawal" or transaction_dict["type"] == "expense":
            if user.balance < transaction_dict["amount"]:
                raise HTTPException(status_code=400, detail="Insufficient balance")
            user.balance -= transaction_dict["amount"]
            await user.save()
        transaction = Transaction()
        for i in transaction_dict:
            if i == "id":
                continue
            transaction.assigned_id = current_user_id
            setattr(transaction, i, transaction_dict[i])
            await transaction.save()
            # transaction_create.inc()
    return Response()


@app.get("/transactions", response_description="List all transactions.")
async def list_transactions(page_size: int = 10, page_number: int = 1, Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()
    current_profile = Authorize.get_raw_jwt().get('profile')
    current_user_id = Authorize.get_raw_jwt().get('user_id')
    if page_number == 0:
        start = page_number * page_size
    else:
        start = (page_number - 1)  * page_size
    if current_profile == Profile.admin:    
        transactions = await Transaction.list_all(start=start, limit=page_size, page_number=page_number)
        if transactions:
            return transactions
        raise HTTPException(status_code=401, detail=f"Transactions not found")
    else:    
        transactions = await Transaction.get_by_user(user_id=current_user_id, start=start, limit=page_size, page_number=page_number)
        if transactions:
            return transactions
        raise HTTPException(status_code=401, detail=f"Transactions not found")


# @app.get('/metrics')
# async def metrics():
#     return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
