from src.database import DB_utils
import json, os

db_handle = DB_utils.DBHandlerAd("data/app.db")

def load_json_as_dict(relative_path):
    # 指定した相対パスを絶対パスに変換
    absolute_path = os.path.abspath(relative_path)
    
    # JSONファイルを開く
    with open(absolute_path, 'r', encoding='utf-8') as file:
        # JSONファイルの内容を辞書型に変換して読み込む
        data = json.load(file)
    
    return data

def insert_message_metaData(meta_data_dict :dict) -> None:
    data = load_json_as_dict("config/db_schema/message.json")
    db_handle.create_table(data)
    id =  db_handle.insert_data("messages", meta_data_dict, check_columns=["gen_id"], last_id=True)
    print(id)

def get_branch_histry(id):
    pass

insert_message_metaData({"gen_id":1})