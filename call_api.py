
import asyncio
import httpx
import json

async def main():
    async with httpx.AsyncClient() as client:
        print("--- /api/project-target/ ---")
        try:
            resp = await client.get("http://localhost:8000/api/project-target/")
            print(f"Status: {resp.status_code}")
            print(json.dumps(resp.json(), indent=2))
        except Exception as e:
            print(f"Error: {e}")

        print("\n--- /api/universal-context/status ---")
        try:
            resp = await client.get("http://localhost:8000/api/universal-context/status")
            print(f"Status: {resp.status_code}")
            print(json.dumps(resp.json(), indent=2))
        except Exception as e:
            print(f"Error: {e}")

        print("\n--- /api/rag/status ---")
        try:
            resp = await client.get("http://localhost:8000/api/rag/status")
            print(f"Status: {resp.status_code}")
            print(json.dumps(resp.json(), indent=2))
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
