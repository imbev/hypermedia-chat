import asyncio
import secrets
import threading

from datastar_py import ServerSentEventGenerator as SSE
from datastar_py.fastapi import DatastarResponse, read_signals
from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

templates = Jinja2Templates(directory="src/templates")

state = {}
state_lock = threading.Lock()

new_message_condition = asyncio.Condition()


def generate_secret():
    return secrets.token_hex()


scroll_script = """
    var el = document.getElementById('messages');
    el.scrollTo({
        top: el.scrollHeight,
        behavior: 'smooth'
    });
"""


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    with state_lock:
        messages = state.get("messages", [])
        users = state.get("users", {-1: generate_secret()})
        user = -1
        while user in users.keys():
            user = secrets.randbelow(10_000)
        users[user] = generate_secret()
        state["users"] = users

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"messages": messages, "user": user, "secret": users[user]},
    )


@app.api_route("/messages", methods=["QUERY"])
async def query_messages(request: Request):
    async def _():
        while True:
            async with new_message_condition:
                messages = state.get("messages", [])
                yield SSE.patch_elements(
                    templates.env.get_template("partials/messages.html").render(
                        {"request": request, "messages": messages}
                    )
                )
                await new_message_condition.wait()

    return DatastarResponse(_())


@app.post("/messages")
async def post_messages(request: Request):
    signals = await read_signals(request)
    if not isinstance(signals, dict):
        return

    user: int = int(signals.get("user", "-1"))
    secret: str = signals.get("secret", "")
    with state_lock:
        users = state.get("users", {})
        if users[user] != secret:
            return

    message: str = signals.get("message", "")
    if message:
        message = message.strip()
    if not message:
        return

    async with new_message_condition:
        with state_lock:
            messages = state.get("messages", [])
            messages.append({"user": user, "content": message})
            state["messages"] = messages
        try:
            new_message_condition.notify_all()
        except RuntimeError:
            pass

    return DatastarResponse(
        [SSE.patch_signals({"message": ""}), SSE.execute_script("message_scroll();")]
    )


app.mount("/static", StaticFiles(directory="src/static"), name="static")
