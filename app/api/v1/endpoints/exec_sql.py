

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


@router.get("/dba", response_class=HTMLResponse)
async def get_sql_form(request: Request):
    return templates.TemplateResponse("dba.html", {"request": request, "results": None, "nonce": 'nonce123'})


@router.post("/execute_sql", response_class=HTMLResponse)
async def execute_sql(request: Request, sql: str = Form(...)):
    try:
        async with engine.connect() as conn:
            # Execute the SQL query asynchronously
            result = await conn.execute(text(sql))

            # For SELECT queries, fetch results
            if sql.strip().lower().startswith("select"):
                columns = result.keys()
                rows = result.fetchall()
                results = {
                    "columns": list(columns),  # Convert to list for JSON serialization
                    "rows": [dict(zip(columns, row)) for row in rows]
                }
            else:
                # For non-SELECT queries, commit changes
                await conn.commit()
                results = {"message": "Query executed successfully"}

        return templates.TemplateResponse("dba.html", {
            "request": request,
            "results": results
        })
    except Exception as e:
        # Handle errors and return them to the template
        return templates.TemplateResponse("dba.html", {
            "request": request,
            "results": {"error": str(e)}
        })

    except Exception as e:

        raise HTTPException(status_code=400, detail=f"SQL Error: {str(e)}")