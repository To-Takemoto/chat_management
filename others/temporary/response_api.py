from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import json
import os
from typing import List, Dict, Any, Optional, AsyncGenerator, Union
from fastapi.responses import StreamingResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では適切なオリジンを指定
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LLMClient:
    def __init__(
            self,
            model: str = "openai/gpt-3.5-turbo",
            url: str = "https://openrouter.ai/api/v1/chat/completions",
            api_key: Optional[str] = None
    ) -> None:
        self.model = model
        self.url = url
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("""API key not found. Please set OPENROUTER_API_KEY environment variable
                              or provide it in the constructor.""")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def post_chat_completion(
            self, messages: List[Dict[str, str]], stream: bool = False
            ) -> Union[Dict[str, Any], AsyncGenerator[str, None]]:
        async with httpx.AsyncClient(http2=True) as client:
            data = {
                "model": self.model,
                "messages": messages,
                "stream": stream
            }
            
            if stream:
                return self._stream_response(client, data)
            else:
                try:
                    response = await client.post(self.url, headers=self.headers, json=data)
                    response.raise_for_status()
                    return response.json()
                except httpx.HTTPError as e:
                    print(f"An HTTP error occurred while making the request: {e}")
                    return {}
                except Exception as e:
                    print(f"An unexpected error occurred: {e}")
                    return {}

    async def _stream_response(self, client: httpx.AsyncClient, data: Dict[str, Any]) -> AsyncGenerator[str, None]:
        try:
            async with client.stream("POST", self.url, headers=self.headers, json=data) as response:
                response.raise_for_status()
                buffer = ""
                async for raw_chunk in response.aiter_raw():
                    buffer += raw_chunk.decode('utf-8')
                    while '\n' in buffer:
                        chunk, buffer = buffer.split('\n', 1)
                        if chunk.strip():
                            parsed = self._parse_chunk(chunk)
                            if parsed:
                                yield parsed
        except httpx.HTTPError as e:
            print(f"An HTTP error occurred while streaming the response: {e}")
        except Exception as e:
            print(f"An unexpected error occurred while streaming: {e}")

    @staticmethod
    def _parse_chunk(chunk: str) -> str:
        chunk = chunk.strip()
        if chunk.startswith("data:"):
            chunk = chunk[5:].strip()
        if chunk == "[DONE]" or ": OPENROUTER" in chunk:
            return ""
        try:
            data = json.loads(chunk)
            content = data['choices'][0]['delta'].get('content', '')
            return content
        except json.JSONDecodeError:
            return ""
        except KeyError:
            return ""

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    stream: bool = False

@app.post("/chat")
async def chat(request: ChatRequest):
    llm = LLMClient()
    if request.stream:
        response_generator = await llm.post_chat_completion(
            [{"role": msg.role, "content": msg.content} for msg in request.messages],
            stream=True
        )
        return StreamingResponse(response_generator, media_type="text/plain")
    else:
        response = await llm.post_chat_completion(
            [{"role": msg.role, "content": msg.content} for msg in request.messages]
        )
        if response:
            return {"choices": response['choices']}
        else:
            raise HTTPException(status_code=500, detail="Failed to get a response")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)