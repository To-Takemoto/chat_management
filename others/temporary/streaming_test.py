import os
import json
import httpx
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse

app = FastAPI()

# APIキーを環境変数から取得
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# HTMLのインターフェースを提供（オプション）
html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
        <style>
            body { font-family: Arial, sans-serif; }
            h1 { text-align: center; }
            form { text-align: center; margin-bottom: 20px; }
            input[type="text"] { width: 300px; padding: 10px; margin-right: 10px; }
            button { padding: 10px 20px; }
            ul { list-style: none; padding: 0; }
            li { padding: 10px; border-bottom: 1px solid #ccc; }
            .user { text-align: right; }
            .assistant { text-align: left; }
            .model-selector { margin-bottom: 20px; text-align: center; }
        </style>
    </head>
    <body>
        <h1>Chat with the Assistant</h1>
        <div class="model-selector">
            <label><input type="radio" name="model" value="anthropic/claude-3-sonnet" checked> Claude 3 Sonnet</label>
            <label><input type="radio" name="model" value="openai/gpt-3.5-turbo"> GPT-3.5 Turbo</label>
        </div>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id="messages">
        </ul>
        <script>
            var ws = new WebSocket("ws://localhost:8000/ws");
            var currentModel = '';

            ws.onmessage = function(event) {
                var messages = document.getElementById('messages');
                var data = JSON.parse(event.data);
                var messageContent = data.content;
                var modelName = data.model;

                var lastMessage = messages.lastElementChild;
                if (!lastMessage || lastMessage.className !== 'assistant') {
                    var message = document.createElement('li');
                    message.className = 'assistant';
                    message.innerHTML = '<strong>' + modelName + ':</strong> ';
                    messages.appendChild(message);
                    lastMessage = message;
                }
                lastMessage.innerHTML += messageContent;
                window.scrollTo(0, document.body.scrollHeight);
            };

            function sendMessage(event) {
                var input = document.getElementById("messageText");
                var messageText = input.value;
                var messages = document.getElementById('messages');
                var message = document.createElement('li');
                var content = document.createTextNode(messageText);
                message.appendChild(content);
                message.className = 'user';
                messages.appendChild(message);

                var selectedModel = document.querySelector('input[name="model"]:checked').value;

                ws.send(JSON.stringify({
                    text: messageText,
                    model: selectedModel
                }));
                
                input.value = '';
                event.preventDefault();
                window.scrollTo(0, document.body.scrollHeight);
            }
        </script>
    </body>
</html>
"""


@app.get("/")
async def get():
    return HTMLResponse(html)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    conversation_history = []

    async with httpx.AsyncClient() as client:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_input = message_data["text"]
            selected_model = message_data["model"]
            conversation_history.append({"role": "user", "content": user_input})

            async with client.stream(
                "POST",
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": selected_model,
                    "messages": conversation_history,
                    "stream": True,
                },
            ) as response:
                assistant_reply = ""
                first_chunk = True
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            json_data = line[len("data: ") :]
                            data = json.loads(json_data)
                            if (
                                "delta" in data["choices"][0]
                                and "content" in data["choices"][0]["delta"]
                            ):
                                content = data["choices"][0]["delta"]["content"]
                                assistant_reply += content
                                if first_chunk:
                                    await websocket.send_text(
                                        json.dumps(
                                            {
                                                "model": selected_model,
                                                "content": content,
                                            }
                                        )
                                    )
                                    first_chunk = False
                                else:
                                    await websocket.send_text(
                                        json.dumps({"model": "", "content": content})
                                    )
                        except (json.JSONDecodeError, KeyError):
                            continue
                conversation_history.append(
                    {"role": "assistant", "content": assistant_reply}
                )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
