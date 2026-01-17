import asyncio
import functools
from fastapi import FastAPI
from contextlib import asynccontextmanager

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def sendMail(sender, receiver, title, message):
    MAIL_APP_PASSWORD = '메일 앱 비밀번호'

    content = MIMEMultipart()
    content["From"] = sender
    content["To"] = receiver
    content["Subject"] = title
    content.attach(MIMEText(message, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as mailsrv:
        mailsrv.login(sender, MAIL_APP_PASSWORD)
        mailsrv.send_message(content)

    return '임시 비밀번호 메일 전송 완료.'

# FastAPI 생애주기(life span) 함수
@asynccontextmanager
async def lifespan(app):
    print('Starting FastAPI App.')
    yield
    print('Stopping FastAPI App.')

app = FastAPI(lifespan=lifespan)

@app.get('/resetpw')
async def resetPW():
    emailAddr = '수신자 주소'
    tempPW = 'imsi123'
    title = '임시 비밀번호'
    message = f'임시 비밀번호: {tempPW}'

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None, 
        functools.partial(sendMail, '발신 메일 계정', emailAddr, title, message)
    )

    return {"success": True, "content": result}

import uvicorn

if __name__ == '__main__':
    uvicorn.run('coro_and_ro2:app', host='0.0.0.0', reload=False, port=8000)