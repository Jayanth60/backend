from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
from psycopg2 import sql
from passlib.context import CryptContext
from fastapi.openapi.docs import get_swagger_ui_html
import uuid
from datetime import datetime

app = FastAPI(docs_url=None)

@app.get("/api", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="Skill-Capital API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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

@app.post("/Insert client/")
async def insert_client(client: Client):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        if check_table_exists("public", "clients"):
            insert_query = sql.SQL('''
                INSERT INTO public.clients (id, email, password, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                ''')
            
            client_id = str(uuid.uuid4())
            hashed_password = pwd_context.hash(client.password)
            created_at = updated_at = datetime.utcnow()
            insert_values = (client_id, client.email, hashed_password, created_at, updated_at)

            cur.execute(insert_query, insert_values)
            conn.commit()
            cur.close()
            conn.close()

            return {"message": f"Client {client.email} added successfully"}
            
        else:
            create_table_query = sql.SQL('''
                CREATE TABLE public.clients (
                    id UUID PRIMARY KEY,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                );
                ALTER TABLE public.clients ADD CONSTRAINT email_non_empty CHECK (email <> '');
                ALTER TABLE public.clients ADD CONSTRAINT password_non_empty CHECK (password <> '');
            ''')

            cur.execute(create_table_query)
            conn.commit()

            client_id = str(uuid.uuid4())
            insert_query = sql.SQL('''
                INSERT INTO public.clients (id, email, password, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                ''')

            hashed_password = pwd_context.hash(client.password)
            created_at = updated_at = datetime.utcnow()
            insert_values = (client_id, client.email, hashed_password, created_at, updated_at)

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
        print(f"Error checking table existence: {error}")
        return False

@app.post('/login')
async def check_client(client: Client):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        query = sql.SQL('''
            SELECT password FROM public.clients WHERE email = %s
        ''')
        cur.execute(query, (client.email,))
        result = cur.fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="Client not found")

        stored_password = result[0]

        if not pwd_context.verify(client.password, stored_password):
            raise HTTPException(status_code=400, detail="Incorrect password")

        cur.close()
        conn.close()

        return {"message": f"Client {client.email} authenticated successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
