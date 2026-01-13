import time
import openai
import asyncio
import functools


#   yield control to an event loop
class YieldToEventLoop:
    def __await__(self):    # cede control to an event loop
        yield

async def asyncCompletion(
    client
    , modelName
    , message
    , streaming=False
    , maxRetries=5
):
    response = None
    startTime = time.time()
    retryCount = 0
    timeout = 45    # seconds

    while (response == None) and (time.time() < startTime + timeout) and (retryCount < maxRetries):
        try:
            # LLM에 스트리밍 요청
            # 이벤트 루프를 블로킹하지 않고, 동기 블로킹 호출을 스레드 풀에서 실행. 
            # streaming=True일 때 동기 이터레이터(예, 리스트 등)가 반환됨. 따라서 완전한 비동기 스트리밍은 아님.
            # loop = asyncio.get_event_loop()
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None
                , functools.partial(
                    client.chat.completions.create
                    , model=modelName
                    , messages=[
                        {"role": 'system', "content": 'You are a helpful assistant. Please answer in Korean.'}
                        , {"role": 'user', "content": message}
                    ]
                    , stream=streaming
                )
            )
            return response
        except asyncio.CancelledError:
            raise
        except Exception as e:
            retryCount = retryCount + 1
            print('asyncCompletion().error (attempt {}):{}'.format(retryCount, e))
            
            if retryCount < maxRetries:
                await YieldToEventLoop()
            else:
                print('asyncCompletion().max retries exceeded.')
                return None

    if time.time() > startTime + timeout:
        print('asyncCompletion().timeout exceeded.')
        return None
