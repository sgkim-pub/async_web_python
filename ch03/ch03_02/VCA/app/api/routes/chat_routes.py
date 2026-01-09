import asyncio
import json

from typing import Annotated
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app import app

chatRouter = APIRouter()

async def sendChunk(
    ws: WebSocket
    , content
):
    """
    This function splits a string content by lines, then sends lines via web socket.

    Args: 
    ws(WebSocket), 
    content(string), 

    Return: Accumulated total response.
    """

    fullResponse = ""

    try:
        lines = content.splitlines(keepends=True)   # preserving \n characters

        for line in lines:
            # 취소 요청이 있는지 확인
            try:
                fullResponse = fullResponse + line
                await ws.send_text(line)
                await asyncio.sleep(0.05)
            except asyncio.CancelledError:
                raise  # 취소 예외를 다시 발생시켜 상위(caller task)로 전파
    except Exception as stream_error:
        print('chat_routes.py.sendChunk().stream_error:', stream_error)
        await ws.send_text('Error: Response generation was interrupted.')
    
    # 스트리밍 완료 후 전체 응답도 전송
    await ws.send_text('--- Full Response: {} ---'.format(fullResponse))

    return fullResponse

@chatRouter.websocket('/chat')
async def chat(
    ws: WebSocket
):
    await ws.accept()
    await ws.send_text('Welcome to the Vibe Coding Assistant!')

    print('chat_routes.py.chat.ws.state: {}'.format(ws.client_state))

    try:
        currentRunCodingAssistantTask = None  # 현재 실행 중인 runCodingAssistant 태스크를 추적
        currentSendChunkTask = None  # 현재 실행 중인 sendChunk 태스크를 추적
        messageQueue = asyncio.Queue()  # 메시지 큐 추가
        
        # 메시지 수신을 위한 별도 태스크
        async def messageReceiver():
            while True:
                try:
                    userMessage = await ws.receive_text()
                    parsedMessage = json.loads(userMessage)

                    if parsedMessage["type"] == "stop":
                        # 현재 실행 중인 runCodingAssistant 태스크가 있다면 취소
                        if currentRunCodingAssistantTask and not currentRunCodingAssistantTask.done():
                            currentRunCodingAssistantTask.cancel()
                            try:
                                await currentRunCodingAssistantTask
                            except asyncio.CancelledError:
                                print('chat_routes.py.chat().messageReceiver().currentRunCodingAssistantTask cancelled.')
                        
                        # 현재 실행 중인 sendChunk 태스크가 있다면 취소
                        if currentSendChunkTask and not currentSendChunkTask.done():
                            currentSendChunkTask.cancel()
                            try:
                                await currentSendChunkTask
                            except asyncio.CancelledError:
                                print('chat_routes.py.chat().messageReceiver().currentSendChunkTask cancelled.')
                
                        await ws.send_text('Response generation stopped.')
                    else:
                        await messageQueue.put(parsedMessage)    # string to dict
                except WebSocketDisconnect:
                    await messageQueue.put({"type": "disconnect"})
                    break
                except Exception as e:
                    print("Message receiver error: {}".format(e))
                    await messageQueue.put({"type": "error", "message": str(e)})
                    break
        
        # 메시지 수신 태스크 시작
        receiverTask = asyncio.create_task(messageReceiver())
        
        while True:
            # 메시지 큐에서 메시지 대기 (비동기)
            userMessage = await messageQueue.get()

            # 연결 종료 처리
            if userMessage["type"] == "disconnect":
                break
            elif userMessage["type"] == "error":
                await ws.send_text('Error: {}'.format(userMessage["message"]))
                continue
            else:   # userMessage["type"] == 'chat'
                message = userMessage["message"]
                print('chat_routes.py.chat().message:', message)

                # app.state를 통해 codingAssistant 접근
                codingAssistant = app.state.codingAssistant
                
                # runCodingAssistant를 태스크로 실행하여 중지 가능하도록 함
                currentRunCodingAssistantTask = asyncio.create_task(
                    codingAssistant.runCodingAssistant('user01', message)
                )
                try:
                    response = await currentRunCodingAssistantTask
                    print('chat_routes.py.chat().codingAssistant.runCodingAssistant().response:\n', response)
                except asyncio.CancelledError:
                    print('chat_routes.py.chat().currentRunCodingAssistantTask cancelled.')
                    currentRunCodingAssistantTask = None
                    continue
                
                currentRunCodingAssistantTask = None
                
                # 응답을 스트리밍으로 전송
                currentSendChunkTask = asyncio.create_task(sendChunk(ws, response))
                try:
                    fullResponse = await currentSendChunkTask
                except asyncio.CancelledError:
                    print('chat_routes.py.chat().currentSendChunkTask cancelled.')
                    currentSendChunkTask = None
                    continue

                currentSendChunkTask = None

                print('chat_routes.py.chat().fullResponse:', fullResponse)

    except WebSocketDisconnect:
        print('WebSocket disconnected.')
        print('chat_routes.py.chat().ws.state:', ws.client_state)
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
