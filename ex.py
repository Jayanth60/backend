from fastapi import FastAPI, HTTPException, Request, Depends, status, Security ,Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
from psycopg2 import sql
from passlib.context import CryptContext
from fastapi.openapi.docs import get_swagger_ui_html
import uuid
from datetime import datetime, timedelta, timezone
import logging
from typing import List
from jose import JWTError, jwt
import secrets
import os
from fastapi.security import OAuth2PasswordBearer
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

app = FastAPI()

SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 3

app = FastAPI(docs_url=None)

@app.get("/", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="Skill-Capital API")

origins = [
    "http://localhost:3000", 
    "http://127.0.0.1:3000" 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_HOST = 'localhost'
DB_NAME = 'postgres'
DB_USER = 'postgres'
DB_PASSWORD = 'jayanth'
DB_PORT = '5432'

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_db_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )
    return conn

class Client(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    email: str

class OAuth2EmailPasswordRequestForm:
    def __init__(self, email: str = Form(...), password: str = Form(...)):
        self.email = email
        self.password = password

class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(status_code=403, detail="Invalid authentication scheme.")
            if not self.verify_jwt(credentials.credentials):
                raise HTTPException(status_code=403, detail="Invalid token or expired token.")
            return credentials.credentials
        else:
            raise HTTPException(status_code=403, detail="Invalid authorization code.")

    def verify_jwt(self, jwtoken: str) -> bool:
        try:
            payload = jwt.decode(jwtoken, SECRET_KEY, algorithms=[ALGORITHM])
        except JWTError:
            return False
        return True

def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@app.post('/login', response_model=Token)
async def check_client(form_data: OAuth2EmailPasswordRequestForm = Depends()):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        query = sql.SQL('''
            SELECT password FROM public.clients WHERE email = %s
        ''')
        cur.execute(query, (form_data.email,))
        result = cur.fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="Client not found")

        stored_password = result[0]

        if not pwd_context.verify(form_data.password, stored_password):
            raise HTTPException(status_code=400, detail="Incorrect password")

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(data={"sub": form_data.email}, expires_delta=access_token_expires)

        cur.close()
        conn.close()

        return {"access_token": access_token, "token_type": "bearer", "email": form_data.email}

    except (Exception, psycopg2.Error) as e:
        raise HTTPException(status_code=500, detail=str(e))


# Custom exception for unauthorized access
credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# def get_current_user(token: str = Depends(oauth2_scheme)):
#     try:
#         # Decode the JWT token
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         email: str = payload.get("sub")
#         if email is None:
#             raise credentials_exception
#         return {"email": email}
#     except JWTError:
#         raise credentials_exception


def get_current_user(token: str = Depends(JWTBearer())):
    try:
        # Decode the JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")  # Retrieve the 'sub' field, which contains the email
        if email is None:
            raise HTTPException(status_code=401, detail="Could not validate credentials")
        return {"email": email}
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")



@app.get("/users")
async def read_users_me(current_user: dict = Security(get_current_user)):
    # Return the authorized user's details
    return {"user": current_user}