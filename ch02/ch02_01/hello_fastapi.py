from fastapi import FastAPI

from contextlib import asynccontextmanager

# 아래는 FastAPI의 생애주기(life span) 함수이다.
@asynccontextmanager
async def lifespan(app):
    print('Starting Hello, FastAPI.')
    yield
    print('Stopping Hello, FastAPI.')

# app = FastAPI()

# 생애주기 함수를 이용하는 경우
app = FastAPI(lifespan=lifespan)

@app.get('/')
def sayHello():
    return {"message": 'Hello, FastAPI!'}

import uvicorn

if __name__ == '__main__':
    print('FastAPI app started.')
    uvicorn.run('hello_fastapi:app', host='0.0.0.0', reload=False, port=8000)
