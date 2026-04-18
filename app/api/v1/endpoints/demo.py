
from fastapi import APIRouter

from app.middleware.custom_cors import custom_cors

router = APIRouter()

'''
接口参数Demo
'''


@router.get("/demo")
@custom_cors(["http://localhost:63342"], methods=["GET", "POST"])
async def home():
    return {"hello": "world"}
