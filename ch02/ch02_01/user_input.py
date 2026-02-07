from fastapi import FastAPI, Depends
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager
from typing import Annotated

@asynccontextmanager
async def lifespan(app):
    print('Starting FastAPI app.')
    yield
    print('Stopping FastAPI app.')

app = FastAPI(lifespan=lifespan)

@app.get("/login")
async def sendLoginPage():
    return FileResponse("ch02/ch02_01/login.html")

from fastapi.security import OAuth2PasswordRequestForm

@app.post("/login", status_code=200)
async def login(
    loginInfo: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    username = loginInfo.username
    password = loginInfo.password

    print('username:', username)
    print('password:', password)

    if username == password:
        respJSON = {
            "success": True
            , "content": f'{username}님 안녕하세요.'
        }
    else:
        respJSON = {
            "success": False 
            , "content": '사용자 이름 또는 비밀번호가 맞지 않습니다.'
        }

    return JSONResponse(content=respJSON)

import uvicorn

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', reload=False, port=8000)
