# import psycopg2 # type: ignore


# host = 'localhost'
# dbname = 'postgres'
# user = 'postgres'
# password = 'jayanth'
# port = '5432'

# conn = psycopg2.connect(
#     host=host,
#     dbname=dbname,
#     user=user,
#     password=password,
#     port=port
# )

# cur = conn.cursor()

# insert_query = '''
#     INSERT INTO public.clients (name)
#     VALUES (%s)
#  '''

# formated_name_string = 'jayanth'


# insert_values = (
#     formated_name_string,
# )

# cur.execute(insert_query, insert_values)

# conn.commit()

# cur.close()
# conn.close()



from fastapi import FastAPI ,HTTPException
from pydantic import BaseModel
import psycopg2
from psycopg2 import sql
from passlib.context import CryptContext

app = FastAPI()

# Database connection parameters
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

@app.post("/Create tables/")
async def create_table():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        insert_query = sql.SQL('''
            CREATE TABLE public.clients (
                email VARCHAR(100) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL);
        ''')

        cur.execute( insert_query)
        conn.commit()

        cur.close()
        conn.close()
        # print(client.name)
        return {"message": "hi"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/Insert client/")
async def insert_client(client: Client):
    # print(client.name)
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        insert_query = sql.SQL('''
            INSERT INTO public.clients (email,password)
            VALUES (%s, %s)
        ''')

        insert_values = (client.email,client.password,)

        cur.execute( insert_query, insert_values)
        conn.commit()

        cur.close()
        conn.close()
        # print(client.name)
        return {"message": f"{client.email,client.password}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# @app.get("/Name of client")
# async def display_client(client: Client):
#     return {"Client Name": f"{client.email}"}

# def get_password_hash(password: str):
#     return pwd_context.hash(password)

# def verify_password(plain_password: str, hashed_password: str):
#     return pwd_context.verify(plain_password, hashed_password)
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
