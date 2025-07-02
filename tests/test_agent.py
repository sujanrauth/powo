import pytest
from ichatbio.agent_response import DirectResponse, ProcessBeginResponse, ProcessLogResponse, ArtifactResponse

from src.agent import POWOAgent


@pytest.mark.asyncio
async def test_powo_agent(context, messages):
    # The test `context` populates the `messages` list with the agent's responses
    await POWOAgent().run(context, "I need Information about Allium Cepa", "", None)

    # Message objects are restricted to the following types:
    messages: list[ ProcessBeginResponse | ProcessLogResponse | ArtifactResponse | DirectResponse ]

    assert messages == [
        ProcessBeginResponse(summary='Analyzing plant request', data=None),
        ProcessLogResponse(text='Identified: Allium Cepa', data={'genus': 'Allium', 'species': 'Cepa'}),
        ProcessLogResponse(text='Searching Kew Gardens database by querying: Allium Cepa', 
                           data={'search_url': 'https://powo.science.kew.org/api/2/search?perPage=500&cursor=%2A&q=genus%3AAllium%2Cspecies%3ACepa&f=species_f'}),
        ArtifactResponse(mimetype='text/markdown', 
                         description='Search results for Allium Cepa', 
                         uris='https://powo.science.kew.org/api/2/search?perPage=500&cursor=%2A&q=genus%3AAllium%2Cspecies%3ACepa&f=species_f', 
                         content=None, 
                         metadata={'genus': 'Allium', 'species': 'Cepa', 'total_found': 1, 'search_url': 'https://powo.science.kew.org/api/2/search?perPage=500&cursor=%2A&q=genus%3AAllium%2Cspecies%3ACepa&f=species_f'}),
        ProcessLogResponse(text='Search completed. Found 1 matching plants.', data={'total_matches': 1}),
        ProcessLogResponse(text='Retrieving plant details by fetching detailed information for 1 plants.', data=None),
        ProcessLogResponse(text='Successfully retrieved 1 plant details.', data=None),
        ArtifactResponse(mimetype='text/markdown', 
                         description='Detailed botanical information for Allium Cepa', 
                         uris=['https://powo.science.kew.org/api/2/taxon/urn:lsid:ipni.org:names:527795-1?fields=distribution'], 
                         content=None, 
                         metadata={'genus': 'Allium', 'species': 'Cepa', 'total_found': 1, 'details_retrieved': 1, 'search_url': 'https://powo.science.kew.org/api/2/search?perPage=500&cursor=%2A&q=genus%3AAllium%2Cspecies%3ACepa&f=species_f', 'plant_details_url': ['https://powo.science.kew.org/api/2/taxon/urn:lsid:ipni.org:names:527795-1?fields=distribution']}),
        DirectResponse(text='Found 1 total matches for Allium Cepa. The artifact contains the complete botanical information.', data=None),
    ]
