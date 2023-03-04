import os 

from pydantic import BaseModel
from datetime import timedelta

UUID_SECRET = '45c86f7ab8044d499f6b8f632167f33f'
JWT_EXPIRE = timedelta(3600)
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "transactionlog")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admintransactionlog")
JWT_SECRET =  UUID_SECRET
DATABASE_URL = os.environ.get("DATABASE_URL", f"mongodb+srv://{ADMIN_USERNAME}:{ADMIN_PASSWORD}@transactionlog.bjcvzu1.mongodb.net/?retryWrites=true&w=majority")
DATABASE_NAME = os.environ.get("DATABASE_NAME", ADMIN_USERNAME)



class Settings(BaseModel):
    authjwt_secret_key: str = JWT_SECRET
    authjwt_access_token_expires= JWT_EXPIRE
    
