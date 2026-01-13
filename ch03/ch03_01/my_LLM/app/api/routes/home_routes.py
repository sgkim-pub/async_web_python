from fastapi import APIRouter
from fastapi.responses import FileResponse

homeRouter = APIRouter()

@homeRouter.get("/")
async def index():
    return FileResponse("app/templates/index.html")

@homeRouter.get("/home")
async def home():
    return FileResponse("app/templates/index.html")

