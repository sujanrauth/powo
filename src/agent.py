import os
from typing import Optional, AsyncGenerator, List, Dict, Any, Literal, override
from urllib.parse import urlencode
import requests
import dotenv
import instructor
from instructor.exceptions import InstructorRetryException
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from ichatbio.agent import IChatBioAgent
from ichatbio.agent_response import ResponseContext, IChatBioAgentProcess
from ichatbio.types import AgentCard, AgentEntrypoint

dotenv.load_dotenv()

# General Plant Model
class Plant(BaseModel):
    fqId: str
    rank: str
    accepted: Optional[bool] = None
    author: Optional[str] = None
    kingdom: Optional[str] = None
    family: Optional[str] = None
    name: Optional[str] = None
    snippet: Optional[str] = None
    url: Optional[str] = None
    images: Optional[Any] = None
    synonymOf: Optional[Dict[str, Any]] = None

# Classification Data Model
class Classification(BaseModel):
    fqId: str
    name: str
    author: Optional[str] = None
    rank: str
    taxonomicStatus: str

# Synonym Data Model
class Synonym(BaseModel):
    fqId: str
    name: str
    author: Optional[str] = None
    rank: str
    taxonomicStatus: str

# Main Plant Data Model
class PlantData(BaseModel):
    modified: str
    bibliographicCitation: str
    genus: str
    taxonomicStatus: str
    kingdom: str
    phylum: str
    clazz: str
    subclass: str
    order: str
    family: str
    nomenclaturalCode: str
    source: str
    namePublishedInYear: int
    taxonRemarks: str
    nomenclaturalStatus: str
    lifeform: str
    climate: str
    hybrid: bool
    paftolId: str
    plantae: bool
    fungi: bool
    locations: List[str]
    synonym: bool
    fqId: str
    name: str
    authors: str
    species: str
    rank: str
    reference: str
    classification: List[Classification]
    synonyms: List[Synonym]


class PlantQueryModel(BaseModel):
    """Extracted plant information from user message"""
    genus: str = Field(..., description="Genus of the plant, e.g Mangifera")
    species: str = Field(..., description="Species of the plant, e.g indica")


class POWOAgent(IChatBioAgent):
    def __init__(self):
        self.agent_card = AgentCard(
            name="POWO Plant Data Agent",
            description="Retrieves detailed plant information from Kew Gardens POWO API using genus and species names.",
            icon=None,
            url="http://localhost:9999",
            entrypoints=[
                AgentEntrypoint(
                    id="get_plant_info",
                    description="Returns detailed botanical information for plants",
                    parameters=None
                )
            ]
        )

    @override
    def get_agent_card(self) -> AgentCard:
        return self.agent_card

    @override
    async def run(self, context: ResponseContext, request: str, entrypoint: str, params: Optional[BaseModel]):
        async with context.begin_process(summary="Analyzing plant request") as process:
            # process: IChatBioAgentProcess

            try:
                openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                instructor_client = instructor.patch(openai_client)

                # Extract plant information from the user request using OpenAI
                plant_query: PlantQueryModel = await instructor_client.chat.completions.create(
                    model="gpt-4",
                    response_model=PlantQueryModel,
                    messages=[
                        {
                            "role": "system",
                            "content": """
                            You are a botanical expert that extracts plant genus and species information from user messages.
                            Instructions:
                            1. Identify the genus and species from the user's message
                            2. If multiple plants are mentioned, focus on the first/main one 
                            """
                        },
                        {"role": "user", "content": request}
                    ],
                    max_retries=3
                )

                await process.log(f"Identified: {plant_query.genus} {plant_query.species}", {
                        "genus": plant_query.genus,
                        "species": plant_query.species,
                    })

                # Search for plants using Kew Gardens API
                search_url = self._build_search_url(plant_query.genus, plant_query.species)
                
                await process.log(f"Searching Kew Gardens database by querying: {plant_query.genus} {plant_query.species}", 
                                  data={"search_url": search_url})

                # Call the serach API to get all the occurances of the given the plant scientific name 
                response = requests.get(search_url)
                if response.status_code != 200:
                    await context.reply(text = "Search failed due to server error")
                    return
                
                # Extract the unique fqids from the search results
                search_data = response.json()
                fqids = self._extract_fqids(search_data)

                if not fqids:
                    await context.reply(f"No plants found matching {plant_query.genus} {plant_query.species}")
                    return
                
                # Create an ArtifactMessage with data from the search api
                await process.create_artifact(
                    mimetype="text/markdown",
                    description=f"Search results for {plant_query.genus} {plant_query.species}",
                    uris=search_url,
                    metadata={
                        "genus": plant_query.genus,
                        "species": plant_query.species,
                        "total_found": len(fqids),
                        "search_url": search_url,
                    }
                )

                await process.log(f"Search completed. Found {len(fqids)} matching plants.", data={"total_matches": len(fqids)})

                # Get detailed information for each fqid
                await process.log(f"Retrieving plant details by fetching detailed information for {len(fqids)} plants.")

                plant_details = []
                plant_details_url = []
                for fqid in fqids:
                    detail_url = f"{os.getenv("BASE_TAXON_URL")}/{fqid}?fields=distribution"

                    # Call the taxon API to get the detailed information about all the search result plants with fqids
                    detail_response = requests.get(detail_url)
                    
                    if detail_response.status_code == 200:
                        plant_details_url.append(detail_url)
                        detail_data = detail_response.json()
                        plant_details.append(detail_data)
            
                await process.log(f"Successfully retrieved {len(plant_details)} plant details.")
                
                # Create an ArtifactMessage with all the data
                await process.create_artifact(
                    mimetype="text/markdown",
                    description=f"Detailed botanical information for {plant_query.genus} {plant_query.species}",
                    uris=plant_details_url,
                    metadata={
                        "genus": plant_query.genus,
                        "species": plant_query.species,
                        "total_found": len(fqids),
                        "details_retrieved": len(plant_details),
                        "search_url": search_url,
                        "plant_details_url": plant_details_url
                    }
                )

                await context.reply(f"Found {len(fqids)} total matches for {plant_query.genus} {plant_query.species}. The artifact contains the complete botanical information.")

            except InstructorRetryException as e:
                await context.reply("Sorry, I couldn't extract plant information from your request.")
            except Exception as e:
                await context.reply("An error occurred while retrieving plant information", data={ "error": str(e)})


    def _build_search_url(self, genus: str, species: str) -> str:
        """Build the search URL for Powo API"""
        params = {
            'perPage': 500,
            'cursor': '*',
            'q': f'genus:{genus},species:{species}',
            'f': 'species_f'
        }
        return f"{os.getenv("BASE_SEARCH_URL")}?{urlencode(params)}"

    def _extract_fqids(self, search_data: Dict[str, Any]) -> List[str]:
        """Extract fqids from search response"""
        fqids = []
        try:
            if 'results' in search_data:
                for result in search_data['results']:
                    if 'fqId' in result:
                        fqids.append(result['fqId'])
        except Exception:
            pass
        return fqids
