from fastapi import FastAPI, HTTPException, Request, Depends, status, Security
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
from psycopg2 import sql
from passlib.context import CryptContext
from fastapi.openapi.docs import get_swagger_ui_html
import uuid
from datetime import datetime, timedelta, timezone
import logging
from jose import JWTError, jwt
import secrets
import os
from fastapi.security import OAuth2PasswordBearer
from fastapi.security import OAuth2PasswordRequestForm
from smtplib import SMTP
import smtplib
import logging
from email.mime.text import MIMEText
from typing import List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

app = FastAPI(docs_url=None)

@app.get("/", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="Skill-Capital API",)

origins = ["http://localhost:3000", "http://127.0.0.1:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True, 
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_HOST = 'localhost'
DB_NAME = 'fastapi'
DB_USER = 'postgres'
DB_PASSWORD = 'jayanth'
DB_PORT = '5432'

SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1
REMEMBER_ME_EXPIRE_DAYS = 1

MAX_FAILED_ATTEMPTS = 6

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
    remember_me: bool = False

class Token(BaseModel):
    access_token: str
    token_type: str
    email: str


class Lead(BaseModel):
    name: str
    cc : str
    phone : str
    email: str
    fee_quoted: int
    batch_timing: str
    description: str
    lead_status : str
    lead_source : str
    stack : str
    course : str
    class_mode : str
    next_followup : datetime
    created_at : datetime

class getLead(BaseModel):
    name: str
    cc: str
    phone: str
    lead_status: str
    stack : str
    class_mode : str
    created_at : datetime

# def send_account_lock_email(email: str):
#     try:
#         # Setup the MIME
#         message = MIMEText("Your account has been locked due to too many failed login attempts.")
#         message["Subject"] = "Account Locked"
#         message["From"] = ""
#         message["To"] = email
#         # print('hi')

#         # SMTP setup for Gmail (replace with your SMTP server)
#         with smtplib.SMTP("smtp.gmail.com", ) as smtp:
#             smtp.starttls()  # Secure the connection
#             smtp.login("", "")  # Login to the email server
#             smtp.send_message(message)  
#         logging.info(f"Account lock email sent to {email}")
# except Exception as e:
    #     logging.error(f"Failed to send account lock email to {email}: {str(e)}")


#Creating clients 
@app.post("/Insert client/")
async def insert_client(client: Client, request: Request):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        if not check_table_exists("public", "clients"):
            create_table_query = sql.SQL('''
                CREATE TABLE public.clients (
                    id UUID PRIMARY KEY,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    remember_me_token BOOLEAN DEFAULT FALSE,
                    failed_attempts INT DEFAULT 0,
                    account_locked BOOLEAN DEFAULT FALSE,
                    ip_address VARCHAR(50)
                );
                ALTER TABLE public.clients ADD CONSTRAINT email_non_empty CHECK (email <> '');
                ALTER TABLE public.clients ADD CONSTRAINT password_non_empty CHECK (password <> '');
            ''')
            cur.execute(create_table_query)
            conn.commit()

        insert_query = sql.SQL('''
            INSERT INTO public.clients (id, email, password, created_at, updated_at, remember_me_token, failed_attempts, account_locked, ip_address)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''')
        
        ip_address = request.client.host
        cur.execute("SELECT id FROM public.clients WHERE ip_address = %s", (ip_address,))
        existing_client = cur.fetchone()

        if existing_client:
            raise HTTPException(status_code=400, detail="An account has already been created from this IP address.")
        
        client_id = str(uuid.uuid4())
        hashed_password = pwd_context.hash(client.password)
        created_at = updated_at = datetime.now(timezone.utc)
        insert_values = (client_id, client.email, hashed_password, created_at, updated_at, client.remember_me, 0, False, ip_address)

        cur.execute(insert_query, insert_values)
        conn.commit()
        cur.close()
        conn.close()

        return {"message": f"Client {client.email} added successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def check_table_exists(schema, table_name):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = sql.SQL(
            "SELECT EXISTS ("
            "SELECT FROM information_schema.tables "
            "WHERE table_schema = %s AND table_name = %s);"
        )
        
        cur.execute(query, (schema, table_name))
        exists = cur.fetchone()[0]
        cur.close()
        conn.close()
       
        return exists
    except (Exception, psycopg2.Error) as error:
        logging.error(f"Error checking table existence: {error}")
        return False

def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


#Access token
@app.post('/login', response_model=Token)
async def check_client(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        query = sql.SQL('''
            SELECT id, password, remember_me_token, failed_attempts, account_locked FROM public.clients WHERE email = %s
        ''')
        cur.execute(query, (form_data.username,))
        result = cur.fetchone()

        if not result:
            log_invalid_attempt(form_data.username, request.client.host)
            raise HTTPException(status_code=404, detail="Client not found")

        user_id, stored_password, remember_me, failed_attempts, account_locked = result

        if account_locked:
            # send_account_lock_email(form_data.username)
            raise HTTPException(status_code=423, detail="Account locked due to too many failed login attempts")

        if not pwd_context.verify(form_data.password, stored_password):
            failed_attempts += 1
            if failed_attempts >= MAX_FAILED_ATTEMPTS:
                cur.execute("UPDATE public.clients SET account_locked = TRUE WHERE id = %s", (user_id,))
                conn.commit()
                raise HTTPException(status_code=423, detail="Account locked due to too many failed login attempts")
            else:
                cur.execute("UPDATE public.clients SET failed_attempts = %s WHERE id = %s", (failed_attempts, user_id))
                conn.commit()
                log_invalid_attempt(form_data.username, request.client.host)
                raise HTTPException(status_code=400, detail="Incorrect password")

        cur.execute("UPDATE public.clients SET failed_attempts = 0 WHERE id = %s", (user_id,))
        conn.commit()

        access_token_expires = timedelta(days=REMEMBER_ME_EXPIRE_DAYS) if remember_me else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(data={"sub": form_data.username}, expires_delta=access_token_expires)

        cur.close()
        conn.close()

        return {"access_token": access_token, "token_type": "bearer", "email": form_data.username}

    except (Exception, psycopg2.Error) as e:
        raise HTTPException(status_code=500, detail=str(e))

def log_invalid_attempt(email: str, ip_address: str):
    logging.warning(f"Invalid login attempt for email: {email} , from IP: {ip_address}")



credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, 
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")  

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        return {"email": email}
    except JWTError:
        raise credentials_exception


# Authorize clients
@app.get("/users")
async def read_users_me(current_user: dict = Security(get_current_user)):
    return {"user": current_user}



# Creating leads
@app.post("/createleads")
async def insert_lead(lead: Lead):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        if not check_table_exists("public", "leads"):
            create_table_query = sql.SQL('''
                CREATE TABLE public.leads (
                    id UUID PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    cc VARCHAR(255) NOT NULL,
                    phone VARCHAR(20) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    fee_quoted INT NOT NULL,
                    batch_timing VARCHAR(50) NOT NULL,
                    description TEXT,
                    lead_status VARCHAR(50) NOT NULL,
                    lead_source VARCHAR(50) NOT NULL,
                    stack VARCHAR(50) NOT NULL,
                    course VARCHAR(50) NOT NULL,
                    class_mode VARCHAR(50) NOT NULL,
                    next_followup TIMESTAMP NOT NULL,
                    created_at TIMESTAMP NOT NULL
                );
            ''')
            cur.execute(create_table_query)
            conn.commit()

        insert_query = sql.SQL('''
            INSERT INTO public.leads (id, name, cc, phone, email, fee_quoted, batch_timing, description, lead_status, lead_source, stack, course, class_mode, next_followup, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s,%s, %s, %s, %s, %s,%s)
            ''')
        client_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)

        values = ( client_id,
            lead.name, lead.cc , lead.phone , lead.email , lead.fee_quoted, lead.batch_timing, lead.description, 
            lead.lead_status , lead.lead_source , lead.stack , lead.course , lead.class_mode , lead.next_followup,
            created_at
        )
        
        cur.execute(insert_query,values)
        conn.commit()
        cur.close()
        conn.close()

        return {"message": f"Client {lead.name} added successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def check_table_exists(schema, table_name):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = sql.SQL(
            "SELECT EXISTS ("
            "SELECT FROM information_schema.tables "
            "WHERE table_schema = %s AND table_name = %s);"
        )
        
        cur.execute(query, (schema, table_name))
        exists = cur.fetchone()[0]
        cur.close()
        conn.close()
       
        return exists
    except (Exception, psycopg2.Error) as error:
        logging.error(f"Error checking table existence: {error}")
        return False

# Getting lead data
@app.get("/getleads", response_model=List[getLead])
async def get_leads():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        if not check_table_exists("public", "leads"):
            raise HTTPException(status_code=404, detail=str('No data to display'))

        select_query = sql.SQL('''
            SELECT name, cc, phone, lead_status, stack, class_mode, created_at
            FROM public.leads;
        ''')

        cur.execute(select_query)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        leads = []
        for row in rows:
            lead = getLead(
                name=row[0],
                cc=row[1],
                phone=row[2],
                lead_status=row[3],
                stack=row[4],
                class_mode=row[5],
                created_at=row[6]
            )
            leads.append(lead)

        return leads

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

#Getting all details for update lead. 
@app.get("/getlead/{lead_id}", response_model=Lead)
async def get_lead(lead_id: str):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        if not check_table_exists("public", "leads"):
            raise HTTPException(status_code=404, detail=str('No data to display'))

        query = sql.SQL('''
            SELECT id, name, cc, phone, email, fee_quoted, batch_timing, description, 
                   lead_status, lead_source, stack, course, class_mode, 
                   next_followup, created_at
            FROM public.leads
            WHERE id = %s
        ''')
        cur.execute(query, (lead_id,))
        lead = cur.fetchone()

        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")

        lead_data = {
            "id": lead[0],
            "name": lead[1],
            "cc": lead[2],
            "phone": lead[3],
            "email": lead[4],
            "fee_quoted": lead[5],
            "batch_timing": lead[6],
            "description": lead[7],
            "lead_status": lead[8],
            "lead_source": lead[9],
            "stack": lead[10],
            "course": lead[11],
            "class_mode": lead[12],
            "next_followup": lead[13],
            "created_at": lead[14]
        }

        cur.close()
        conn.close()

        return lead_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Update lead
@app.put("/updatelead/{lead_id}")
async def update_lead(lead_id: str, lead: Lead):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        if not check_table_exists("public", "leads"):
            raise HTTPException(status_code=404, detail=str('No data to update'))
        

        query = sql.SQL('''
            SELECT id FROM public.leads WHERE id = %s
        ''')
        cur.execute(query, (lead_id,))
        existing_lead = cur.fetchone()

        if not existing_lead:
            raise HTTPException(status_code=404, detail="Lead not found")

        update_query = sql.SQL('''
            UPDATE public.leads
            SET name = %s,
                cc = %s,
                phone = %s,
                email = %s,
                fee_quoted = %s,
                batch_timing = %s,
                description = %s,
                lead_status = %s,
                lead_source = %s,
                stack = %s,
                course = %s,
                class_mode = %s,
                next_followup = %s,
                created_at = %s
            WHERE id = %s
        ''')

        updated_values = (
            lead.name, lead.cc, lead.phone, lead.email, lead.fee_quoted,
            lead.batch_timing, lead.description, lead.lead_status, lead.lead_source,
            lead.stack, lead.course, lead.class_mode, lead.next_followup, lead.created_at, lead_id
        )

        cur.execute(update_query, updated_values)
        conn.commit()
        cur.close()
        conn.close()

        return {"message": f"Lead {lead.name} updated successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

# Delete leads
@app.delete("/deletelead/{lead_id}")
async def delete_lead(lead_id: str):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        if not check_table_exists("public", "leads"):
            raise HTTPException(status_code=404, detail=str('No data to delete'))

        query = sql.SQL('''
            SELECT id,name FROM public.leads WHERE id = %s
        ''')
        cur.execute(query, (lead_id,))
        existing_lead = cur.fetchone()
        id, name = existing_lead

        if not existing_lead:
            raise HTTPException(status_code=404, detail="Lead not found")

        delete_query = sql.SQL('''
            DELETE FROM public.leads WHERE id = %s
        ''')
        cur.execute(delete_query, (lead_id,))
        conn.commit()

        cur.close()
        conn.close()

        return {"message": f"Lead {name} deleted successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
