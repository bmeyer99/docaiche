import asyncio
import os

async def main():
    import aiosqlite
    db_path = "./data/docaiche.db"
    if not os.path.exists(db_path):
        print("DB file not found:", db_path)
        return
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT config_key, config_value FROM system_config") as cursor:
            rows = await cursor.fetchall()
            if not rows:
                print("No rows in system_config")
            for key, value in rows:
                print(f"{key} = {value}")

if __name__ == "__main__":
    asyncio.run(main())