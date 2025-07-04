import asyncio
from src.database.connection import DatabaseManager

async def main():
    db = DatabaseManager()
    await db.connect()
    
    # Count documents
    count = await db.count_documents()
    print(f"Total documents in system: {count}")
    
    # Check workspaces
    workspaces = await db.get_all_workspaces()
    print(f"Total workspaces: {len(workspaces)}")
    for ws in workspaces[:5]:
        print(f"  - {ws['slug']}: {ws['doc_count']} docs")
    
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())