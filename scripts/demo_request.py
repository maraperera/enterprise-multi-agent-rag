import asyncio
import httpx


async def main():
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post("http://localhost:8000/v1/research", json={"question": "What are our AI governance requirements?"})
        response.raise_for_status()
        print(response.json())


if __name__ == "__main__":
    asyncio.run(main())
