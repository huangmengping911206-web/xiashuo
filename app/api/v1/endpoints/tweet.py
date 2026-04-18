

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from sqlalchemy import text

from app.core.check_user import get_user_or_401
from app.database.session import engine



router = APIRouter()

'''
执行SQL
'''
templates = Jinja2Templates(directory="templates")


@router.get("/index", response_class=HTMLResponse)
async def get_sql_form(request: Request):
    return templates.TemplateResponse("tweet_index.html", {"request": request, "results": None, "nonce": 'nonce123'})

