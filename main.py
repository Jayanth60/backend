from fastapi import FastAPI ,HTTPException
from pydantic import BaseModel
import psycopg2
from psycopg2 import sql
from passlib.context import CryptContext
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

app = FastAPI(docs_url=None)  # Disable the default /docs

@app.get("/api", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="API Docs")

DB_HOST = 'localhost'
DB_NAME = 'postgres'
DB_USER = 'postgres'
DB_PASSWORD = 'jayanth'
DB_PORT = '5432'

# Database connection function
def get_db_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )
    return conn

# Pydantic model for client
class Client(BaseModel):
    email: str
    password: str
    
@app.post("/Insert client/")
async def insert_client(client: Client):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        if (check_table_exists("public", "clients")):
            insert_query = sql.SQL('''
                INSERT INTO public.clients (email,password)
                VALUES (%s, %s)
                ''')
            
            insert_values = (client.email,client.password,)

            cur.execute( insert_query, insert_values)

            conn.commit()

            cur.close()
            conn.close()

            return {"message": f"{client.email,client.password}"}
            
        else:
            insert_query_1 = sql.SQL('''
                CREATE TABLE public.clients (
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL);
                    ALTER TABLE public.clients ADD CONSTRAINT email_non_empty CHECK (email <> '');
                    ALTER TABLE public.clients ADD CONSTRAINT password_non_empty CHECK (password <> '');''')

            insert_values = (client.email,client.password,)


            cur.execute( insert_query_1,)

            insert_query = sql.SQL('''
                INSERT INTO public.clients (email,password)
                VALUES (%s, %s)
                ''')

            insert_values = (client.email,client.password,)


            cur.execute( insert_query, insert_values)

            conn.commit()

            cur.close()
            conn.close()

            return {"message": f"{client.email,client.password}"}

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

    
# @app.get("/Name of client")
# async def display_client(client: Client):
#     return {"Client Name": f"{client.email}"}

# def get_password_hash(password: str):
#     return pwd_context.hash(password)

# def verify_password(plain_password: str, hashed_password: str):
#     return pwd_context.verify(plain_password, hashed_password)
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")