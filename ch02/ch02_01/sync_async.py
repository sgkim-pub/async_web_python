from datetime import datetime
import time

from fastapi import FastAPI
import uvicorn

app = FastAPI()

# 동기 방식 처리
def syncTask(name):
    print('Sync task:', name)
    time.sleep(1)
    return name

@app.get('/synctask')
def syncRun():
    now = datetime.now()
    results = [syncTask('A'), syncTask('B'), syncTask('C')]
    print('syncRun() running time:', datetime.now() - now)

    return {"result": results}

import asyncio

# 비동기 방식 처리
async def asyncTask(name):
    print('Async task:', name)
    await asyncio.sleep(1)
    return name

@app.get('/asynctask')
async def asyncRun():
    now = datetime.now()
    results = await asyncio.gather(asyncTask('A'), asyncTask('B'), asyncTask('C'))
    print('asyncRun() running time:', datetime.now() - now)

    return {"result": results}

if __name__ == "__main__":
    uvicorn.run("sync_async:app", host="0.0.0.0", reload=False, port=8000)
