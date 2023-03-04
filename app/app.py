from typing import List
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from fastapi_jwt_auth.exceptions import AuthJWTException
from fastapi.middleware.cors import CORSMiddleware
from settings import Settings

from schemas import Client
from fastapi_jwt_auth import AuthJWT
from users import User, UserLogin, Profile

from settings import JWT_EXPIRE, ADMIN_PASSWORD, ADMIN_USERNAME 

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.post("/clients", response_description="Create a client.", response_model=Client)
async def create_client(client_dict: Client):
    client = Client()
    data = client_dict.dict(exclude_unset=True)
    for i in data:
        if i == 'id':
            continue
        setattr(client, i, data[i])
    await client.save()
    return client

@app.get("/clients", response_description="List all clients.")
async def list_client(page_size: int = 10, page_number: int = 1, Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()
    if page_number == 0:
        start = page_number * page_size
    else:
        start = (page_number - 1)  * page_size
    clients = await Client.list_all(start=start, limit=page_size, page_number=page_number)
    if clients:
        return clients
    raise HTTPException(status_code=401, detail=f"Not found")

@app.get("/clients/{client_id}", response_description="List one client")
async def show_client(client_id: str, Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()
    client = await Client.get(client_id)
    if client is not None:
        return client
    raise HTTPException(status_code=401, detail=f"No client found with {client_id}")

@app.put("/clients/{client_id}", response_description="update a single client", response_model=Client)
async def update_client(client_id: str, client_up: Client, Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()
    current_profile = Authorize.get_raw_jwt().get("profile")
    if current_profile == Profile.admin:
        client = await Client.get_without_subjects_career(client_id)
        if client is not None:
            if client:
                data = client_up.dict(exclude_unset=True)
                for i in data:
                    if i == 'id':
                        continue
                    setattr(client,i, data[i])
                await client.save()
            return client
        raise HTTPException(status_code=404, detail=f"tag {client_id} not found")
    raise HTTPException(status_code=401, detail=f"You dont have permissions to delete.")
    
@app.delete("/clients/{client_id}", response_description="delete a single client", operation_id="authorize")
async def delete_client(client_id: str, Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()
    current_profile = Authorize.get_raw_jwt().get("profile")
    if current_profile == Profile.admin:
        client = await Client.get_without_subjects_career(client_id)
        if client is not None:
            await client.delete()
            return True
        raise HTTPException(status_code=404, detail=f"tag {client_id} not found")
    raise HTTPException(status_code=401, detail=f"You dont have permissions to delete.")
