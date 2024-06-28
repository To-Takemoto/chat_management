'''
目次
DBHandler
    data_exists             :特定のデータが存在しているかを先にverify
    insert_data             :上と連携して、データinsert時に重複があった場合はスキップできる関数
    select_one_record       :任意のレコード(列)を取り出す関数
    count_data              :対象テーブルにどれだけデータが格納されてるかをintで返す
    get_columns             :対象テーブルのカラムを返す
    create_table            :与えられたスキーマに従ってテーブルを作る関数
    table_exists            :指定した名前のテーブルが存在するか量る

DBHandlerAd
    drop_table              :任意のテーブルを削除する
    drop_record             :任意のテーブルの、任意のレコードを削除する
'''


import sqlite3, json

#下の関数はDBに接続するためのデコレータ
def db_connection(func):
    def wrapper(self, *args, **kwargs):
        # コネクションが既に開かれているかチェック
        if not hasattr(self, 'conn') or self.conn is None:
            new_connection = True
            self.conn = sqlite3.connect(self.db_path)
            self.cur = self.conn.cursor()
        else:
            new_connection = False

        try:
            return func(self, *args, **kwargs)
        finally:
            if new_connection:
                self.conn.commit()
                self.cur.close()
                self.conn.close()
                del self.cur
                del self.conn
    return wrapper

#したの関数はエラーハンドリングを追加するデコレータ
def error_handling(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except sqlite3.Error as e:
            print(f"{func.__name__}のメソッドにてエラー")
            print(f"An error occurred: {e}")
        except Exception as e:
            print(f"{func.__name__}のメソッドにてエラー")
            print(f"An unexpected error occurred: {e}")
    return wrapper

########こっからhandler部分########
class DBHandler:
    def __init__(self, db_path) -> None:
        """
        db_pathで接続先を設定。絶対パスを入れてネ
        """
        self.db_path = db_path

    @db_connection
    @error_handling
    def data_exists(self, table_name :str, data: dict, check_columns :list = None) -> bool:
        """
        dataで渡されたデータと、check_columsで指定されたカラムの中に同様のデータがすでに存在しているか否かを量る。
        あった場合はTrue、なかった場合はFalseを返す
        """
        if check_columns is None:
            check_columns = data.keys()

        query = f"SELECT * FROM {table_name} WHERE " + " AND ".join([f"{k} = ?" for k in check_columns])
        check_values = [data[k] for k in check_columns]
        self.cur.execute(query, tuple(check_values))
        exists = self.cur.fetchone() is not None
        if exists:
            return True
        else:
            return False
    
    @db_connection
    @error_handling
    def insert_data(self,
                    table_name :str,
                    data :dict, check_columns :list = None,
                    hard :bool = None,
                    last_id :bool = False
                    ) -> bool:
        """
        概要 : データを挿入するメソッド
        table_name : isnert先のテーブルを指定。テーブルが存在していないとエラーになる。
        data : isnertしたいデータ。キーにテーブルのカラム名、バリューに実際に挿入したいデータを入れる。
        check_columns : 挿入したいデータがすこの指定されたリストの中のカラムに含まれる場合は挿入を飛ばす。指定しない場合、すべてのカラムが検証される。
        hard : Trueを入れると、データの検証を飛ばし、データの有無に関わらず挿入する。
        """
        if not hard:
            if self.data_exists(table_name, data, check_columns) == True:
                print("Data already exists with specified columns, skipping insert.")
                return False
        columns = ",".join(data.keys())
        values = ",".join(["?"] * len(data))
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({values});"
        self.cur.execute(query, tuple(data.values()))
        if last_id:
            last_id = self.cur.lastrowid
            return last_id
        else:
            return True
        

    @db_connection
    @error_handling
    def select_one_record(self, table_name :str, conditions :str = None, fields :str = None) -> tuple:
        """
        概要 : レコード(行)を一列取り出してくれるメソッド。
        table_name : isnert先のテーブルを指定。テーブルが存在していないとエラーになる。
        data : isnertしたいデータ。キーにテーブルのカラム名、バリューに実際に挿入したいデータを入れる。
        fields : 引きたいデータのカラムを指定する。
        """
        query = f"SELECT {fields or '*'} FROM {table_name}"
        if conditions:
            query += f" WHERE {conditions}"
            
        self.cur.execute(query)
        record = self.cur.fetchone()
        return record
    
    @db_connection
    @error_handling
    def count_data(self, table_name :str) -> int:
        """
        概要 : 対象のテーブルのレコード数をカウントしてくれるメソッド。
        table_name : データのカウントする対象
        """
        sql_select = f'SELECT COUNT(*) FROM {table_name};'
        self.cur.execute(sql_select)

        result = self.cur.fetchone()
        if result:
            return result[0]
        else:
            return 0
        
    @db_connection
    @error_handling
    def get_columns(self, table_name :str) -> tuple:
        """
        任意のテーブルのカラムをタプルとして取得するするメソッド。
        table_name : 対象のテーブル
        """
        self.cur.execute(f"PRAGMA table_info({table_name});")
        columns = [tup[1] for tup in self.cur.fetchall()]
        return columns
        
    @db_connection
    @error_handling
    def get_column_data(self, table_name: str, column_name: str) -> list:
        """
        概要 : カラム(列)のデータを一列文引っ張ってくるメソッド。
        table_name : 対象のテーブル
        column_name : 対象のカラム
        """
        
        query = f"SELECT {column_name} FROM {table_name};"
        
        self.cur.execute(query)
        data = self.cur.fetchall()
        
        # Extracting the column data from the tuple format
        column_data = [item[0] for item in data]

        return column_data
    
    @db_connection
    @error_handling   
    def create_table(self, schema :dict, table_name :str = None) -> None:
        """
        与えられたカラムとテーブル名に従ってDBに新たにテーブルを作るための関数
        schema : テーブルのスキーマ情報
        table_name : 任意でテーブル名を指定する
        """
        if table_name == None:
            table_name = schema["table_name"]
        columns = schema["columns"]

        columns_sql = ", ".join([f"{col['name']} {col['type']}" for col in columns])
        create_table_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_sql});"

        self.cur.execute(create_table_sql)

    @db_connection
    @error_handling 
    def table_exists(self, table_name) -> bool:
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
        self.cur.execute(query, (table_name,))
        result = self.cur.fetchone()
        if result:
            return True
        else:
            return False
        
    @db_connection
    @error_handling
    def insert_json(self, table_name: str, json_data: dict, last_id) -> bool:
        """
        概要 : JSONデータを指定されたテーブルに挿入するメソッド。
        table_name : insert先のテーブルを指定。テーブルが存在していないとエラーになる。
        json_data : insertしたいJSONデータ。キーにテーブルのカラム名、バリューに実際に挿入したいデータを入れる。
        """
        json_str = json.dumps(json_data)
        data = {'json_data': json_str}
        columns = ",".join(data.keys())
        values = ",".join(["?"] * len(data))
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({values});"
        self.cur.execute(query, tuple(data.values()))
        if last_id:
            last_id = self.cur.lastrowid
            return last_id

    @db_connection
    @error_handling
    def select_json(self, table_name: str, conditions: str = None) -> dict:
        """
        概要 : 指定された条件でJSONデータを取得するメソッド。
        table_name : select先のテーブルを指定。テーブルが存在していないとエラーになる。
        conditions : select条件を指定。
        """
        query = f"SELECT json_data FROM {table_name}"
        if conditions:
            query += f" WHERE {conditions}"
        self.cur.execute(query)
        result = self.cur.fetchone()
        if result:
            return json.loads(result[0])
        return {}
    
    @db_connection
    @error_handling
    def update_data(self, table_name: str, data: dict, conditions: dict) -> bool:
        """
        概要: 特定の条件に基づいてデータを更新するメソッド。
        table_name: 更新対象のテーブルを指定。
        data: 更新したいデータ。キーにテーブルのカラム名、バリューに新しいデータを入れる。
        conditions: 更新条件を指定する辞書。キーにカラム名、バリューに条件の値を入れる。
        """
        set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
        where_clause = " AND ".join([f"{k} = ?" for k in conditions.keys()])
        query = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}"
        values = list(data.values()) + list(conditions.values())
        self.cur.execute(query, tuple(values))
        return True
    

class DBHandlerAd(DBHandler):
    def __init__(self, db_path) -> None:
        super().__init__(db_path)

    @db_connection
    @error_handling
    def drop_table(self, table_name):
        """

        """
        self.cur.execute(f"DROP TABLE {table_name}")

    @db_connection
    @error_handling
    def drop_record(self, table_name, column, value):
        """

        """
        sql = f"DELETE FROM {table_name} WHERE {column} = ?"
        self.cur.execute(sql, (value,))