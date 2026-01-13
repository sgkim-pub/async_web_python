from fastapi import APIRouter, Form, Depends
from fastapi.responses import FileResponse, JSONResponse

userRouter = APIRouter()

@userRouter.get("/signup")
async def sendSignupPage():
    return FileResponse("app/templates/signup.html")

from app.services.user import User
from typing import Annotated

@userRouter.post("/signup")    # 201: Created
async def signup(
    userService: Annotated[User, Depends(User)]
    , username: str = Form(...)
    , password: str = Form(...)
):
    existingUser = await userService.getUserInfoByName(username)

    if existingUser is None:
        lastrowid = await userService.createUser(username, password)

        respJSON = {
            "success": True
            , "content": ''
        }
        statusCode = 201
    else:
        respJSON = {
            "success": False
            , "content": '같은 이름의 사용자가 있습니다.'
        }
        statusCode = 200

    return JSONResponse(content=respJSON, status_code=statusCode)

@userRouter.get("/signup_complete")
async def signup_complete():
    return FileResponse("app/templates/signup_complete.html")

@userRouter.get("/login")
async def sendLoginPage():
    return FileResponse("app/templates/login.html")

from fastapi.security import OAuth2PasswordRequestForm

@userRouter.post("/login", status_code=200)
async def login(
    loginInfo: Annotated[OAuth2PasswordRequestForm, Depends()]
    , userService: Annotated[User, Depends(User)]
):
    userInfo = await userService.veryfyUserByName(loginInfo.username, loginInfo.password)

    if userInfo is not None:
        tokenPayload = {
            "id": userInfo["id"]
            , "username": userInfo["username"]
            , "picture": userInfo["picture"]
            , "last_login_at": userInfo["last_login_at"]
        }
        accessToken = userService.createAccessToken(tokenPayload)

        respJSON = {
            "success": True
            , "content": {"access_token": accessToken, "token_type": 'bearer'}
        }
    else:
        respJSON = {
            "success": False
            , "content": "사용자 이름 또는 비밀번호가 일치하지 않습니다."
        }

    return JSONResponse(content=respJSON)

@userRouter.get("/logout", status_code=200)
async def sendLogoutPage():
    return FileResponse("app/templates/logout.html")

@userRouter.get("/chat", status_code=200)
async def sendChatPage():
    return FileResponse("app/templates/chat.html")

@userRouter.get("/close_account", status_code=200)
async def sendCloseAccountPage():
    return FileResponse("app/templates/close_account.html")

from fastapi.security import OAuth2PasswordBearer

oauth2Scheme = OAuth2PasswordBearer(tokenUrl='/login')  # get access token in HTTP header.

@userRouter.post("/close_account", status_code=200)
async def closeAccount(
    token: Annotated[str, Depends(oauth2Scheme)]
    , userService: Annotated[User, Depends(User)]
    , password: str = Form(...)
):
    payload = userService.decodeAccessToken(token)
    id = payload["id"]

    check = await userService.verifyUserById(id, password)

    if check:
        await userService.deleteUserById(id)

        jsonResp = {
            "success": True 
            , "content": '계정이 삭제되었습니다.'
        }
    else:
        jsonResp = {
            "success": False
            , "content": '비밀번호가 일치하지 않습니다.'
        }
    
    return JSONResponse(content=jsonResp)

@userRouter.get("/close_account_complete", status_code=200)
async def sendCloseAccountCompletePage():
    return FileResponse("app/templates/close_account_complete.html")

