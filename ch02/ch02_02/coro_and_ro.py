import time
import asyncio

def blocking():
    time.sleep(0.5)
    return '{} Blocking!'.format(time.ctime())

async def main():
    print('{} Hello!'.format(time.ctime()))
    
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, blocking)
    print(result)
    
    await asyncio.sleep(1.0)
    print('{} Goodbye!'.format(time.ctime()))

asyncio.run(main())
