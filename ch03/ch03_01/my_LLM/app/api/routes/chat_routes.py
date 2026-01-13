from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import Annotated
import openai
import json
import asyncio
import litellm

from app.services.user import User
from app.utils.semantic_cache import SemanticCache
from app.services.async_llm_api import asyncCompletion

chatRouter = APIRouter()

oauth2Scheme = OAuth2PasswordBearer(tokenUrl='/user/login')

@chatRouter.get('/cache/info')
async def getCacheInfo(
    token: Annotated[str, Depends(oauth2Scheme)]
    , userService: Annotated[User, Depends(User)]
):
    """ 캐시 컬렉션의 상세 정보를 반환합니다. """
    payload = userService.decodeAccessToken(token)
    colName = payload["username"].replace('@', '_')

    semanticCache = SemanticCache(collectionName=colName)
    info = semanticCache.getCollectionInfo()

    # info: 
    # {
    #     "total_records": ...
    #     , "latest_timestamp": ...
    #     , "latest_timestamp_YMDHMS": ...
    #     , "collection_name": ... 
    # }

    return info

async def sendChunk(
    ws: WebSocket
    , content
    , cached=False
):
    fullResponse = ""

    # 캐시 응답 전송
    if cached:
        chunks = content.split(' ')
        for chunk in chunks:
            # 취소 요청이 있는지 확인
            try:
                fullResponse = fullResponse + chunk + ' '
                await ws.send_text('Assistant: {}'.format(chunk + ' '))
                await asyncio.sleep(0.05)
            except asyncio.CancelledError:
                raise  # 취소 예외를 다시 발생시켜 상위로 전파
        await ws.send_text('--- Full Response: {} ---'.format(content))
    # 스트리밍 응답 전송
    else:
        try:
            for chunk in content:
                try:
                    if len(chunk.choices) > 0:
                        if chunk.choices[0].delta.content is not None:
                            chunkContent = chunk.choices[0].delta.content
                            fullResponse = fullResponse + chunkContent
                            await ws.send_text('Assistant: {}'.format(chunkContent))
                            await asyncio.sleep(0.05)
                        else:   # no data to send
                            pass
                    else:   # the last chunk - usage info.
                        pass
                except asyncio.CancelledError:
                    raise  # 취소 예외를 다시 발생시켜 상위로 전파
        except Exception as stream_error:
            print('chat_routes.py.chat().stream_error:', stream_error)
            await ws.send_text('Error: Response generation was interrupted.')
    
        # 스트리밍 완료 후 전체 응답도 전송
        await ws.send_text('--- Full Response: {} ---'.format(fullResponse))

    return fullResponse

async def asyncSendChunk(
    ws: WebSocket
    , content
    , cached=False
):
    fullResponse = ""

    # 캐시 응답 전송
    if cached:
        chunks = content.split(' ')
        for chunk in chunks:
            # 취소 요청이 있는지 확인
            try:
                fullResponse = fullResponse + chunk + ' '
                await ws.send_text('Assistant: {}'.format(chunk + ' '))
                await asyncio.sleep(0.05)
            except asyncio.CancelledError:
                raise  # 취소 예외를 다시 발생시켜 상위로 전파
        await ws.send_text('--- Full Response: {} ---'.format(content))
    # 스트리밍 응답 전송
    else:
        try:
            async for chunk in content:   # async iterator
                try:
                    if len(chunk.choices) > 0:
                        if chunk.choices[0].delta.content is not None:
                            chunkContent = chunk.choices[0].delta.content
                            fullResponse = fullResponse + chunkContent
                            await ws.send_text('Assistant: {}'.format(chunkContent))
                            await asyncio.sleep(0.05)
                        else:   # no data to send
                            pass
                    else:   # the last chunk - usage info.
                        pass
                except asyncio.CancelledError:
                    raise  # 취소 예외를 다시 발생시켜 상위로 전파
        except Exception as stream_error:
            print('chat_routes.py.chat().stream_error:', stream_error)
            await ws.send_text('Error: Response generation was interrupted.')
            # continue
    
        # 스트리밍 완료 후 전체 응답도 전송
        await ws.send_text('--- Full Response: {} ---'.format(fullResponse))

    return fullResponse

@chatRouter.websocket('/chat')
async def chat(
    ws: WebSocket
    , userService: Annotated[User, Depends(User)]
):
    await ws.accept()
    await ws.send_text('Server: Welcome to the chat!')
    print('chat_routes.py.chat.ws.state: {}'.format(ws.client_state))

    client = openai.OpenAI(
        base_url='http://localhost:8080/v1'
        , api_key='no-key-required'
    )

    try:
        currentSendChunkTask = None  # 현재 실행 중인 sendChunk 태스크를 추적
        currentCompletionTask = None  # 현재 실행 중인 asyncCompletion 태스크를 추적
        messageQueue = asyncio.Queue()  # 메시지 큐
        
        async def messageReceiver():
            while True:
                try:
                    userMessage = await ws.receive_text()
                    parsedMessage = json.loads(userMessage)

                    if parsedMessage["type"] == "stop":
                        if currentCompletionTask and not currentCompletionTask.done():
                            currentCompletionTask.cancel()
                            try:
                                await currentCompletionTask
                            except asyncio.CancelledError:
                                print('chat_routes.py.chat().messageReceiver().Completion task cancelled.')

                        if currentSendChunkTask and not currentSendChunkTask.done():
                            currentSendChunkTask.cancel()
                            try:
                                await currentSendChunkTask
                            except asyncio.CancelledError:
                                print('chat_routes.py.chat().messageReceiver().sendChunk task cancelled.')
                
                        await ws.send_text('Server: Response generation stopped.')
                    else:
                        await messageQueue.put(parsedMessage)    # string to dict
                except WebSocketDisconnect:
                    await messageQueue.put({"type": "disconnect"})
                    break
                except Exception as e:
                    print("Message receiver error: {}".format(e))
                    await messageQueue.put({"type": "error", "message": str(e)})
                    break
        
        receiverTask = asyncio.create_task(messageReceiver())
        
        while True:
            userMessage = await messageQueue.get()

            if userMessage["type"] == "disconnect":
                break
            elif userMessage["type"] == "error":
                await ws.send_text('Error: {}'.format(userMessage["message"]))
                continue
            # for customized semantic cache collection for each user
            elif userMessage["type"] == 'auth':
                if userMessage["message"] is not None:
                    authToken = userMessage["message"]
                    payload = userService.decodeAccessToken(authToken)

                    colName = payload["username"].replace('@', '_')
                    semanticCache = SemanticCache(collectionName=colName)
                else:
                    semanticCache = SemanticCache() # use default collection
            else:   # userMessage["type"] == 'chat'
                message = userMessage["message"]
                print('chat_routes.py.chat().message:', message)

                cachedCompletion = semanticCache.queryToCache(message)
                print('semanticCache.queryToCache(message):', cachedCompletion)

                if cachedCompletion is not None and cachedCompletion["distance"] < 0.05:
                    content = cachedCompletion["response"]
                    currentSendChunkTask = asyncio.create_task(sendChunk(ws, content, True))
                    try:
                        full_response = await currentSendChunkTask
                    except asyncio.CancelledError:
                        print('chat_routes.py.chat().sendChunk() task for sending cached response cancelled.')
                    finally:
                        currentSendChunkTask = None
                else:
                    currentCompletionTask = asyncio.create_task(asyncCompletion(client, 'Phi-4-mini-instruct', message, True))
                    try:
                        response = await currentCompletionTask
                    except asyncio.CancelledError:
                        print('chat_routes.py.chat().Completion task cancelled.')
                        continue
                    except Exception as e:
                        print('chat_routes.py.chat().Completion task error:', e)
                        continue
                    finally:
                        currentCompletionTask = None

                    currentSendChunkTask = asyncio.create_task(sendChunk(ws, response, False))
                    try:
                        full_response = await currentSendChunkTask
                    except asyncio.CancelledError:
                        print('chat_routes.py.chat().sendChunk() task cancelled.')
                        continue
                    finally:
                        currentSendChunkTask = None

                    # # 참고: 시간, 토큰 수 등 LLM 사용량 추적을 위한 콜백 함수
                    # def trackCostCallback(kwargs, completionResp, startTime, endTime):
                    #     try:
                    #         respCost = kwargs.get("response_cost", 0)
                    #         print('chat_routes.py.chat().trackCostCallback().respCost:', respCost)
                    #         print('chat_routes.py.chat().trackCostCallback().kwargs:', kwargs)
                    #         print('chat_routes.py.chat().trackCostCallback().completionResp:', completionResp)
                    #         print('chat_routes.py.chat().trackCostCallback().startTime:', startTime)
                    #         print('chat_routes.py.chat().trackCostCallback().endTime:', endTime)
                    #     except Exception as e:
                    #         print('chat_routes.py.chat().trackCostCallback().error:', e)

                    # litellm.success_callback = [trackCostCallback]    # set success callbacks - litellm
    
                    # # LLM에 스트리밍 요청(async) - Litellm
                    # currentCompletionTask = asyncio.create_task(
                    #     litellm.acompletion(
                    #         model='ollama/gemma3:4b'
                    #         , messages=[
                    #             {"role": 'system', "content": 'You are a helpful assistant. Please answer in Korean.'}
                    #             , {"role": 'user', "content": message}
                    #         ]
                    #         , stream=True
                    #     )
                    # )
                    # try:
                    #     response = await currentCompletionTask
                    # except asyncio.CancelledError:
                    #     print('chat_routes.py.chat().Completion task(litellm.acompletion) cancelled.')
                    #     continue
                    # except Exception as e:
                    #     print('chat_routes.py.chat().Completion task(litellm.acompletion) error:', e)
                    #     continue
                    # finally:
                    #     currentCompletionTask = None
    
                    # currentSendChunkTask = asyncio.create_task(asyncSendChunk(ws, response, False))
                    # try:
                    #     full_response = await currentSendChunkTask
                    # except asyncio.CancelledError:
                    #     print('chat_routes.py.chat().sendChunk() task cancelled.')
                    #     continue
                    # finally:
                    #     currentSendChunkTask = None

                    semanticCache.addToCache(message, full_response)
                    colInfo = semanticCache.getCollectionInfo()
                    print('chat_routes.py.chat().semanticCache.getCollectionInfo():', colInfo)

    except WebSocketDisconnect:
        print('WebSocket disconnected.')
        print('web_socket.py.echoWS().ws.state:', ws.client_state)
    except Exception as e:
        print('chat_routes.py.chat().e:', e)
        await ws.send_text('Error: {}'.format(str(e)))
    finally:
        # 메시지 수신 태스크 정리
        if 'receiverTask' in locals() and not receiverTask.done():
            receiverTask.cancel()
            try:
                await receiverTask
            except asyncio.CancelledError:
                pass
