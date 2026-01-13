from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.app_config import AppConfig

appCfg = AppConfig("config.json")

import aiomysql

pool = None

async def createConnectionPool(host, portNum, username, password, dbname, minPoolsize, maxPoolsize):
    global pool

    pool = await aiomysql.create_pool(
        host=host
        , port=portNum
        , user=username
        , password=password
        , db=dbname
        , minsize=minPoolsize
        , maxsize=maxPoolsize
    )

async def deleteConnectionPool():
    global pool

    if pool:
        pool.close()
        await pool.wait_closed()
        pool = None

@asynccontextmanager
async def lifespan(app):
    print('Starting FastAPI app.')
    await createConnectionPool('localhost', 3306, appCfg.DB_USER, appCfg.DB_PASSWORD, appCfg.DB, 1, 10)
    yield
    print('Stopping FastAPI app.')
    await deleteConnectionPool()

app = FastAPI(lifespan=lifespan)

from app.api.routes import home_routes
app.include_router(home_routes.homeRouter)

from app.api.routes import user_routes
app.include_router(user_routes.userRouter)

from app.api.routes import chat_routes
app.include_router(chat_routes.chatRouter)
