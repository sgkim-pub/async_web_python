from datetime import datetime, timedelta, timezone
import aiomysql
from jose import JWTError, jwt

from app.utils.db import loadQuery
from app.utils.crypto import encrypt, verify

class User():
    def __init__(self):
        from app import pool

        self.pool = pool

        from app import appCfg

        self.SECRET_KEY = appCfg.JWT_SECRET
        self.ALGORITHM = appCfg.JWT_ALGORITHM

    async def getUserInfoByName(self, username):
        query = loadQuery("get_userinfo_by_username.sql")

        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, (username,))

            userInfo = await cursor.fetchone()

        if userInfo is None:
            return None
        else:
            return userInfo

    async def createUser(self, username, password):
        encryptedPW = encrypt(password)
        query = loadQuery("create_user.sql")

        currentTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, (username, encryptedPW, None, 0, currentTime))
            
            await conn.commit()

            lastrowid = cursor.lastrowid    # lastrowid: primary key value of the table.

        return lastrowid

    async def veryfyUserByName(self, username, password):
        query = loadQuery("get_userinfo_by_username.sql")

        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, (username,))

            userInfo = await cursor.fetchone()

        if userInfo is None:
            return None
        else:
            check = verify(password, userInfo["password"])

            if check:
                return userInfo
            else:
                return None

    # payload: {"id": '...', "username": '...', "picture": '...', "last_login_at": '...'}
    def createAccessToken(self, payload, duration=timedelta(hours=1)):
        expire = datetime.now(timezone.utc) + duration
        payload.update({"exp": expire}) # append "exp" field

        # payload: {"id": '...', "username": '...', "picture": '...', "last_login_at": '...', "exp": '...'}
        accessToken = jwt.encode(payload, self.SECRET_KEY, algorithm=self.ALGORITHM)

        return accessToken

    def decodeAccessToken(self, token):
        try:
            return jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
        except JWTError:
            return None

    async def verifyUserById(self, id, password):
        query = loadQuery("get_userinfo_by_id.sql")

        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, (id,))

            userInfo = await cursor.fetchone()

        if userInfo is None:
            return False
        else:
            check = verify(password, userInfo["password"])
            return check

    async def deleteUserById(self, id):
        query = loadQuery("delete_user_by_id.sql")

        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, (id,))

            await conn.commit()
