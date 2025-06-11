import pytest

from powo_agent.agent import POWOAgent, EmptyModel
from ichatbio.types import ArtifactMessage, ProcessMessage


@pytest.mark.asyncio
async def test_powo():
    agent = POWOAgent()
    response = agent.run("I need Information about Allium Cepa", "", EmptyModel)
    messages = [m async for m in response]

    process_summaries = [p.summary for p in messages if type(p) is ProcessMessage and p.summary]

    assert process_summaries == [
        "Analyzing plant request",
        "Plant information extracted",
        "Searching Kew Gardens database",
        "Search completed",
        "Retrieving plant details",
        "Plant details retrieved"
    ]

    artifacts = [p for p in messages if type(p) is ArtifactMessage]
    assert len(artifacts) == 1

    artifact = artifacts[0]
    assert artifact.mimetype == "text/markdown"
