import requests
import json
import os

# 環境変数の中のapiキーを読み込み
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

class LLMClient:
    def __init__(
            self,
            model: str = None,
            role: str = None,
            url: str = None
    ) -> None:
        self.model = model or "openai/gpt-3.5-turbo"
        self.role = role or "user"
        self.url = url or "https://openrouter.ai/api/v1/chat/completions"
        
    def __enter__(self):
        return self
    
    def __exit__(self, ex_type, ex_value, trace) -> None:
        if ex_type:
            print("exit: ", ex_type, ex_value, trace)

    def post_basic_response(self, content) -> dict:
        response = requests.post(
            url=self.url,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            data=json.dumps({
                "model": self.model,
                "messages": [
                    {"role": self.role, "content": content}
                ]
            })
        )
        return response.json()

def main():
    with LLMClient() as llm:
        res = llm.post_basic_response("こんにちは！")
        print(res)

if __name__ == "__main__":
    main()