import httpx
import json
import os
from typing import List, Dict, Any, Optional, AsyncGenerator, Union
import asyncio


class LLMClient:
    def __init__(
        self,
        model: str = "openai/gpt-3.5-turbo",
        url: str = "https://openrouter.ai/api/v1/chat/completions",
        api_key: Optional[str] = None,
    ) -> None:
        self.model = model
        self.url = url
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("""API key not found. Please set OPENROUTER_API_KEY environment variable
                              or provide it in the constructor.""")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        self.client = httpx.AsyncClient(http2=True)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        await self.client.aclose()
        if exc_type:
            print(f"An error occurred: {exc_type.__name__}: {exc_value}")

    async def post_chat_completion(
        self, messages: List[Dict[str, str]], stream: bool = False
    ) -> Dict[str, Any] | AsyncGenerator[str, None]:
        data = {"model": self.model, "messages": messages, "stream": stream}

        if stream:
            return self._stream_response(data)
        else:
            try:
                response = await self.client.post(
                    self.url, headers=self.headers, json=data
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                print(f"An HTTP error occurred while making the request: {e}")
                return {}
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                return {}

    async def _stream_response(self, data: Dict[str, Any]) -> AsyncGenerator[str, None]:
        try:
            async with self.client.stream(
                "POST", self.url, headers=self.headers, json=data
            ) as response:
                response.raise_for_status()
                buffer = ""
                async for raw_chunk in response.aiter_raw():
                    buffer += raw_chunk.decode("utf-8")
                    while "\n" in buffer:
                        chunk, buffer = buffer.split("\n", 1)
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
            content = data["choices"][0]["delta"].get("content", "")
            return content
        except json.JSONDecodeError:
            return ""
        except KeyError:
            return ""


async def main():
    async with LLMClient() as llm:
        messages = [
            {
                "role": "system",
                "content": "あなたはuserにとって非常に役に立つアシスタントです",
            },
            {"role": "user", "content": " 何か雑学を教えてくれませんか"},
        ]

        # Non-streaming example
        print("Non-streaming response:")
        res = await llm.post_chat_completion(messages)
        if res:
            print(res["choices"][0]["message"]["content"])
        else:
            print("Failed to get a response.")

        print("\nStreaming response:")
        # Streaming example
        async for chunk in await llm.post_chat_completion(messages, stream=True):
            print(chunk, end="", flush=True)
        print()  # Add a newline at the end of the streaming response


if __name__ == "__main__":
    asyncio.run(main())
