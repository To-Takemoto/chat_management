import requests
import json
import os
import httpx

#環境変数の中のapiキーを読み込み
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

class LLMClient:
    def __init__(
            self,
            model: str = None,
            role: str = None,
            url: str = None
    ) -> None:
        #コーディングサポートに長たらしいの出てくるのは嫌なので下にデフォルト値の設定などは移す
        if not model:
            self.model = "openai/gpt-3.5-turbo"
        if not role:
            self.role = "user"
        if not url:
            self.url = "https://openrouter.ai/api/v1/chat/completions"
        
    def __enter__(self):
        return self
    
    def __exit__(self, ex_type, ex_value, trace) -> None:
        if ex_type:
            print("exit: ", ex_type, ex_value, trace)

    def post_basic_response(self, content) -> dict:
        response = requests.post(
        url = "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        },
        data = json.dumps({
            "model": self.model,
            "messages": [
            { "role": self.role, "content": content }
            ]
        })
        )

        return response
    
    async def post_streaming_response(self, content_):
        conversation_history =[]
        async with httpx.AsyncClient() as client:
            state = True
            while state == True:
                conversation_history.append({"role": "user", "content": content_})
                async with self.create_streamer(client, conversation_history) as streamer:
                    assistant_reply = ""
                    async for line in streamer.aiter_lines():
                        if line.startswith("data: "):
                            try:
                                content = self.extracter(line)
                                assistant_reply += content
                                print(content, end='', flush=True)  # 行末の改行を防ぐためにend=''を使用
                            except (json.JSONDecodeError, KeyError):
                                # 解析エラーやキーエラーが発生した場合は次の行へ
                                continue
                    # アシスタントの応答を会話履歴に追加
                    print()  # 改行
                    conversation_history.append({"role": "assistant", "content": assistant_reply})

    async def create_streamer(self, client: httpx.AsyncClient, conversation_history: list) -> httpx.AsyncClient.stream:
        async with client.stream(
            "POST",
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "anthropic/claude-3-sonnet",  # モデル指定（オプション）
                "messages": conversation_history,
                "stream": True  # ストリーミングを有効にする
            }) as streamer:
            return streamer
        
    def extracter(self, line :dict):
        # 'data: 'プレフィックスを削除
        json_data = line[len("data: "):]
        # JSONデータを解析
        data = json.loads(json_data)
        # contentが空でない場合にチャットレスポンスを出力
        if "delta" in data["choices"][0] and "content" in data["choices"][0]["delta"]:
            content = data["choices"][0]["delta"]["content"]
        return content

async def main():
    with LLMClient() as llm:
        res = await llm.post_streaming_response("こんにちは！")
        await print(res.json()["choices"][0]["message"]["content"])

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())