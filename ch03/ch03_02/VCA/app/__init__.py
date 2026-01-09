import os

from fastapi import FastAPI
from contextlib import asynccontextmanager
from getpass import getpass

from app.services.vca import CodingAssistant

@asynccontextmanager
async def lifespan(app: FastAPI):
    print('Starting FastAPI app.')
    apiKey = os.environ.get('GOOGLE_API_KEY')
    if not apiKey:
        apiKey = getpass('Enter your Google API key: ')     # API key 값 설정을 위해 getpass()를 쓰면 코드는 그대로 공유해도 되고, 실행하는 사람이 자기 키를 입력하면 된다.
        print('apiKey:', apiKey)

    # app.state를 사용하여 상태 저장 (전역 변수 대신)
    app.state.codingAssistant = CodingAssistant(apiKey)
    yield
    print('Stopping FastAPI app.')

app = FastAPI(lifespan=lifespan)

from app.api.routes import home_routes
app.include_router(home_routes.homeRouter)

from app.api.routes import chat_routes
app.include_router(chat_routes.chatRouter)
