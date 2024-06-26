import asyncio
import json
import logging
import os
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

# ロギングの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LLMClient:
    """A client for interacting with LLM APIs."""

    def __init__(
        self,
        model: str = "openai/gpt-3.5-turbo",
        url: str = "https://openrouter.ai/api/v1/chat/completions",
        api_key: Optional[str] = None,
    ) -> None:
        """
        Initialize the LLMClient.

        Args:
            model (str): The model to use for completions.
            url (str): The API endpoint URL.
            api_key (Optional[str]): The API key. If not provided, it will be read from the OPENROUTER_API_KEY environment variable.

        Raises:
            ValueError: If the API key is not provided and not found in the environment variables.
        """
        self.model = model
        self.url = url

        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key not found. Please set OPENROUTER_API_KEY environment variable or provide it in the constructor."
            )
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        self.client = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient(http2=True)
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        if self.client:
            await self.client.aclose()
        if exc_type:
            logger.error(f"An error occurred: {exc_type.__name__}: {exc_value}")

    async def post_chat_completion(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        include_meta_data: bool = False,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ) -> Dict[str, Any] | AsyncGenerator[str | Dict[str, Any], None]:
        """
        Post a chat completion request to the API.

        Args:
            messages (List[Dict[str, str]]): The messages to send to the API.
            stream (bool): Whether to stream the response.
            include_meta_data (bool): Whether to include metadata in the response.
            max_retries (int): Maximum number of retries for failed requests.
            backoff_factor (float): Factor to determine the delay between retries.

        Returns:
            Dict[str, Any] | AsyncGenerator[str | Dict[str, Any], None]: The API response or a generator of response chunks.

        Raises:
            httpx.HTTPError: If an HTTP error occurs after all retries have been exhausted.
            RuntimeError: If the client is not initialized.
        """
        if not self.client:
            raise RuntimeError("Client is not initialized. Use 'async with' to initialize the client.")

        data = {"model": self.model, "messages": messages, "stream": stream}

        if stream:
            return self._stream_response(data, include_meta_data, max_retries, backoff_factor)
        else:
            for attempt in range(max_retries):
                try:
                    response = await self.client.post(
                        self.url, headers=self.headers, json=data
                    )
                    response.raise_for_status()
                    response_data = response.json()
                    if not include_meta_data:
                        response_data = response_data["choices"][0]["message"]["content"]
                    return response_data
                except httpx.HTTPError as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Failed to get response after {max_retries} attempts: {e}")
                        raise
                    wait_time = backoff_factor * (2 ** attempt)
                    logger.warning(f"Request failed. Retrying in {wait_time:.2f} seconds...")
                    await asyncio.sleep(wait_time)
                except Exception as e:
                    logger.error(f"An unexpected error occurred: {e}")
                    raise

    async def _stream_response(
        self,
        data: Dict[str, Any],
        include_meta_data: bool,
        max_retries: int,
        backoff_factor: float,
    ) -> AsyncGenerator[str | Dict[str, Any], None]:
        for attempt in range(max_retries):
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
                                parsed_data = self._parse_chunk(chunk)
                                if isinstance(parsed_data, str):
                                    yield parsed_data
                                elif isinstance(parsed_data, dict) and include_meta_data:
                                    yield parsed_data
                return
            except httpx.HTTPError as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to stream response after {max_retries} attempts: {e}")
                    raise
                wait_time = backoff_factor * (2 ** attempt)
                logger.warning(f"Streaming failed. Retrying in {wait_time:.2f} seconds...")
                await asyncio.sleep(wait_time)
            except Exception as e:
                logger.error(f"An unexpected error occurred while streaming: {e}")
                raise

    def _parse_chunk(self, chunk: str) -> str | Dict[str, Any]:
        chunk = chunk.strip()
        if chunk.startswith("data:"):
            chunk = chunk[5:].strip()
        #chunk = chunk.lstrip("data:").strip()←こうだと何故かダメ!
        if chunk == "[DONE]" or ": OPENROUTER" in chunk:
            return ""
        try:
            data = json.loads(chunk)
            if "usage" in data:
                return self._extract_meta_data(data)
            content = data["choices"][0]["delta"].get("content", "")
            return content
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON: {chunk}")
            return chunk
        except KeyError as e:
            logger.warning(f"Unexpected data structure: {e}")
            return ""
        
    @staticmethod
    def _extract_meta_data(data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": data.get("id"),
            "model": data.get("model"),
            "prompt_tokens": data.get("usage", {}).get("prompt_tokens"),#usageというdictの中にさらに内包されているためこういう書き方
            "completion_tokens": data.get("usage", {}).get("completion_tokens"),
            "created": data.get("created"),
            "object": data.get("object"),
            "system_fingerprint": data.get("system_fingerprint")
        }

async def main():
    async with LLMClient() as llm:
        messages = [
            {
                "role": "system",
                "content": "あなたはuserにとって非常に役に立つアシスタントです",
            },
            {
                "role": "user",
                "content": "何か雑学を教えてくれませんか"
            },
        ]

        logger.info("Starting response:")
        try:
            result = await llm.post_chat_completion(messages, stream=False, include_meta_data=False)
            if isinstance(result, str):
                print(result, end="", flush=True)
            elif isinstance(result, dict):
                print(f"\nmetadata: {result}")
        except Exception as e:
            logger.error(f"Error during response: {e}")
        print()  # Add a newline at the end of the response

if __name__ == "__main__":
    asyncio.run(main())