from agent import POWOAgent, EmptyModel
import asyncio

async def agent_checker():
    agent = POWOAgent()
    response = agent.run("I need Information about Allium Cepa", "", EmptyModel)
    async for item in response:
        print(item)

asyncio.run(agent_checker())
