import os
from typing import Optional, AsyncGenerator, List, Dict, Any, Literal, override
from urllib.parse import urlencode
import requests
import dotenv
import instructor
from instructor.exceptions import InstructorRetryException
from openai import AsyncOpenAI
from pydantic import BaseModel, Field, ValidationError
from ichatbio.agent import IChatBioAgent
from ichatbio.agent_response import ResponseContext, IChatBioAgentProcess
from ichatbio.types import AgentCard, AgentEntrypoint

dotenv.load_dotenv()

# Result part of the response from the Search API
class PlantResult(BaseModel):
    fqId: str
    rank: str
    accepted: Optional[bool] = None
    author: Optional[str] = None
    kingdom: Optional[str] = None
    family: Optional[str] = None
    name: Optional[str] = None
    snippet: Optional[str] = None
    url: Optional[str] = None
    images: Optional[List[Any]] = None

# Search API Response model
class PlantSearchResponse(BaseModel):
    totalResults: int
    page: int
    totalPages: int
    perPage: int
    cursor: Optional[str]
    message: Optional[str]
    results: List[PlantResult]

# Classification structure
class Classification(BaseModel):
    fqId: str
    name: str
    author: Optional[str]
    rank: str
    taxonomicStatus: str

# synonym structure
class Synonym(BaseModel):
    fqId: str
    name: str
    author: Optional[str]
    rank: str
    taxonomicStatus: str

# Distribution locations
class DistributionLocation(BaseModel):
    featureId: int
    tdwgCode: str
    tdwgLevel: int
    establishment: str
    locationTree: List[str]
    name: str

# Distribution details 
class Distribution(BaseModel):
    natives: Optional[List[DistributionLocation]] = []
    introduced: Optional[List[DistributionLocation]] = []

# Geometry Envelope Point
class EnvelopePoint(BaseModel):
    x: float
    y: float
    z: Optional[str]

# Main Plant Data Model
class PlantDetail(BaseModel):
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
    taxonRemarks: Optional[str]
    nomenclaturalStatus: Optional[str]
    lifeform: Optional[str]
    climate: Optional[str]
    hybrid: bool
    paftolId: Optional[str] = None
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
    basionymOf: Optional[List[Synonym]] = []
    distribution: Optional[Distribution] = None
    distributionEnvelope: Optional[List[EnvelopePoint]] = []

class PlantQueryModel(BaseModel):
    """Extracted plant information from user message"""
    genus: str = Field(..., description="Genus of the plant, e.g Mangifera")
    species: str = Field(..., description="Species of the plant, e.g indica")


class POWOAgent(IChatBioAgent):
    def __init__(self):
        self.agent_card = AgentCard(
            name="POWO Plant Data Agent",
            description="Retrieves detailed plant information from Kew Gardens POWO and IPNI data source using genus and species names.",
            icon=None,
            # url="http://localhost:29201", #change it based on deployment site
            url="https://powoagent.duckdns.org",
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
        async with context.begin_process(summary="Analyzing plant data request") as process:
            # process: IChatBioAgentProcess

            try:
                openai_client = AsyncOpenAI( base_url=os.getenv("AI_BASE_URL"), api_key=os.getenv("AI_KEY"))
                instructor_client = instructor.patch(openai_client)

                # Extract plant information from the user request using OpenAI
                plant_query: PlantQueryModel = await instructor_client.chat.completions.create(
                    model="llama-3.3-70b-instruct",
                    response_model=PlantQueryModel,
                    messages=[
                        {
                            "role": "system",
                            "content": """
                            You are a botanical expert that extracts plant genus and species information from user messages.
                            Instructions:
                            1. Identify the genus and species from the user's message
                            2. If multiple plants are mentioned, focus on the first/main one 
                            3. Always respond **only** in this strict JSON format (no prose):

                            ```json
                            {
                            "genus": "GenusName",
                            "species": "SpeciesName"
                            }```
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
                
                await process.log(f"Searching Kew Gardens Plants of the World Online(POWO) database.", 
                                  data={"genus": plant_query.genus, "species": plant_query.species, "search_url": search_url,})

                # Call the serach API to get all the occurances of the given the plant scientific name 
                response = requests.get(search_url)
                if response.status_code != 200:
                    await context.reply(text = "Search failed due to server error")
                    return
                
                # validate serach query response
                try:
                    PlantSearchResponse.model_validate(response.json()) 
                except ValidationError as e:
                    await context.reply( "Search query response validation error", data={"error": e.errors(), "raw": response.json() })
                
                # Extract the unique fqids from the search results
                search_data = response.json()
                fqids = self._extract_fqids(search_data)

                if not fqids:
                    await context.reply(f"No plants found matching {plant_query.genus} {plant_query.species}")
                    return
                
                # Create an ArtifactMessage with data from the search api
                await process.create_artifact(
                    mimetype="text/markdown",
                    description=f"Search results for {plant_query.genus} {plant_query.species} from POWO",
                    uris=[search_url],
                    metadata={
                        "genus": plant_query.genus,
                        "species": plant_query.species,
                        "total_found": len(fqids),
                        "search_url": search_url,
                    }
                )

                await process.log(f"Search completed. Found {len(fqids)} matching plants.", data={"total_matches": len(fqids)})

                # Get detailed information for each fqid
                await process.log(f"Retrieving detailed information from Kew Gardens International Plant Names Index(IPNI) for {len(fqids)} plants.")

                plant_details = []
                plant_details_url = []
                for fqid in fqids:
                    detail_url = f"{os.getenv("BASE_TAXON_URL")}/{fqid}?fields=distribution"

                    # Call the taxon API to get the detailed information about all the search result plants with fqids
                    detail_response = requests.get(detail_url)
                    
                    if detail_response.status_code == 200:
                        try:
                            PlantDetail.model_validate(detail_response.json())
                        except ValidationError as e:
                            await context.reply("Plant detail response validation error", data={"error": e.errors()})
                            return
                        plant_details_url.append(detail_url)
                        detail_data = detail_response.json()
                        plant_details.append(detail_data)
            
                await process.log(f"Successfully retrieved {len(plant_details)} plant details.")
                
                # Create an ArtifactMessage with all the data
                await process.create_artifact(
                    mimetype="text/markdown",
                    description=f"Detailed botanical information for {plant_query.genus} {plant_query.species} from IPNI",
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
                await context.reply("Sorry, I couldn't extract plant information from your request.", data={ "error": str(e)})
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
