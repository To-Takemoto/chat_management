#うごかねぇよこんなクソコード！！！！！



from src.database import DB_utils
import json, os
from typing import Dict, Any

db_handle = DB_utils.DBHandlerAd("data/app.db")
user_id = 1

import requests
import json
import os

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def get_response(history):
    response = requests.post(
    url="https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    },
    data=json.dumps({
        "model": "openai/gpt-3.5-turbo", # Optional
        "messages":history
    })
    )

    return response.json()

def extract_meta_data(data: Dict[str, Any], content:str) -> Dict[str, Any]:
    return {
        "gen_id": data.get("id"),
        "model": data.get("model"),
        "prompt_tokens": data.get("usage", {}).get("prompt_tokens"),#usageというdictの中にさらに内包されているためこういう書き方
        "completion_tokens": data.get("usage", {}).get("completion_tokens"),
        "created": data.get("created"),
        #"object": data.get("object"),
        #"system_fingerprint": data.get("system_fingerprint")
    }

def extract_meta_data(data: Dict[str, Any], content:str) -> Dict[str, Any]:
    return {
        "gen_id": data.get("id"),
        "model": data.get("model"),
        "prompt_tokens": data.get("usage", {}).get("prompt_tokens"),
        "completion_tokens": data.get("usage", {}).get("completion_tokens"),
        "created": data.get("created"),
        "content": content
    }

def main(first_system_message:dict, db_handle :DB_utils.DBHandler):
    id_branch = []
    history = []
    state = True
    if first_system_message:
        history.append(first_system_message)

        fsm_id = db_handle.insert_data(
            "system_messages",
            {"user_id":user_id, "content":first_system_message['content']},
            last_id=True
            )
        id_branch.append({"system":fsm_id})
        branch_id = db_handle.insert_json(
            "branches",
            id_branch,
            last_id=True
            )
        
    while state == True:
        input_ = input("you :")
        if input_ == "終了":
            break

        user_message_dict = {"role":"user", "content":input_}
        history.append(user_message_dict)

        recent_m_id = db_handle.insert_data(
            "user_messages",
            {"user_id":user_id, "content":input_},
            last_id= True
            )
        id_branch.append({"user":recent_m_id})
        db_handle.update_data("branches", {"json_data":id_branch}, {"id":branch_id})

        resp = get_response(history)
        llm_content = resp["choices"][0]["message"]["content"]
        print(llm_content)
        history.append({"role":"assistant", "content":llm_content})

        resp_dict = extract_meta_data(resp, llm_content)
        resp_dict |= {"user_id":user_id}

        recent_l_id = db_handle.insert_data(
            "llm_messages",
            resp_dict,
            last_id=True
            )
        id_branch.append({"assistant":recent_l_id})
        db_handle.update_data("branches", {"json_data":id_branch}, {"id":branch_id})

main({"role":"system", "content":"あなたは優秀なアシスタントです"}, db_handle)


# def insert_llm_message(meta_data_dict :dict) -> None:
#     id = db_handle.insert_data("llm_messages", meta_data_dict, check_columns=["gen_id"], last_id=True)
#     return id

# def insert_user_message(user_data_dict :dict) -> None:
#     id = db_handle.insert_data("user_messages", user_data_dict, last_id=True)
#     return id

# def insert_system_message(system_message_dict :dict) -> None:
#     id = db_handle.insert_data("system_massage", system_message_dict, last_id=True)
#     return id