import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, select

# データベースの設定
DATABASE_URL = "sqlite+aiosqlite:///data/app.db"
engine = create_async_engine(DATABASE_URL, echo=True)
Base = declarative_base()


# モデルの定義
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    age = Column(Integer)


# テーブルの作成
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


asyncio.run(init_db())

# セッションの作成
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


# データの追加
async def add_user(name: str, age: int):
    async with async_session() as session:
        async with session.begin():
            new_user = User(name=name, age=age)
            session.add(new_user)
        await session.commit()


asyncio.run(add_user("Jane Doe", 25))


# データのクエリ
async def get_users():
    async with async_session() as session:
        stmt = select(User)
        result = await session.execute(stmt)
        users = result.scalars().all()
        for user in users:
            print(user)


asyncio.run(get_users())
