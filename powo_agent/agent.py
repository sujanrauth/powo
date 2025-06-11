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
from ichatbio.types import AgentCard, AgentEntrypoint, ProcessMessage, Message, TextMessage, ArtifactMessage
import pykew.powo as powo
from pykew.powo_terms import Name, Filters

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

class EmptyModel(BaseModel):
    """Just an Empty model so stop the parameter error in the AgentEntrypoint"""
    ...

class POWOAgent(IChatBioAgent):
    def __init__(self):
        self.agent_card = AgentCard(
            name="POWO Plant Data Agent",
            description="Retrieves detailed plant information from Kew Gardens POWO API using genus and species names.",
            url="http://localhost:9999",
            icon=None,
            entrypoints=[
                AgentEntrypoint(
                    id="get_plant_info",
                    description="Returns detailed botanical information for plants",
                    parameters=EmptyModel
                )
            ]
        )

    @override
    def get_agent_card(self) -> AgentCard:
        return self.agent_card

    @override
    async def run(self, request: str, entrypoint: str, params: Optional[BaseModel]) -> AsyncGenerator[Message, None]:
        openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        instructor_client = instructor.patch(openai_client)

        try:
            yield ProcessMessage(summary="Analyzing plant request", description="Extracting genus and species from user message")

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

            yield ProcessMessage(
                summary="Plant information extracted",
                description=f"Identified: {plant_query.genus} {plant_query.species}",
                data={
                    "genus": plant_query.genus,
                    "species": plant_query.species,
                }
            )

            # Search for plants using Kew Gardens API
            search_url = self._build_search_url(plant_query.genus, plant_query.species)
            
            yield ProcessMessage(
                summary="Searching Kew Gardens database",
                description=f"Querying: {plant_query.genus} {plant_query.species}",
                data={"search_url": search_url}
            )

            # Call the serach API to get all the occurances of the given the plant scientific name 
            response = requests.get(search_url)
            if response.status_code != 200:
                yield TextMessage(text=f"Search failed due to server error")
                return
            
            # Extract the unique fqids from the search results
            search_data = response.json()
            fqids = self._extract_fqids(search_data)

            if not fqids:
                yield TextMessage(text=f"No plants found matching {plant_query.genus} {plant_query.species}")
                return

            yield ProcessMessage(
                summary="Search completed",
                description=f"Found {len(fqids)} matching plants",
                data={"total_matches": len(fqids)}
            )

            # Get detailed information for each fqid
            yield ProcessMessage(
                summary="Retrieving plant details",
                description=f"Fetching detailed information for {len(fqids)} plants"
            )

            plant_details = []
            plant_details_url = []
            for fqid in fqids:
                detail_url = f"{os.getenv("BASE_TAXON_URL")}/{fqid}"

                # Call the taxon API to get the detailed information about all the search result plants with fqids
                detail_response = requests.get(detail_url)
                
                if detail_response.status_code == 200:
                    plant_details_url.append(detail_url)
                    detail_data = detail_response.json()
                    plant_details.append(detail_data)
           
            yield ProcessMessage(
                summary="Plant details retrieved",
                description=f"Successfully retrieved {len(plant_details)} plant details",
            )
            
            # Create an ArtifactMessage with all the data
            yield ArtifactMessage(
                mimetype="text/markdown",
                description=f"Detailed botanical information for {plant_query.genus} {plant_query.species}",
                content=None,
                metadata={
                    "genus": plant_query.genus,
                    "species": plant_query.species,
                    "total_found": len(fqids),
                    "details_retrieved": len(plant_details),
                    "search_url": search_url,
                    "plant_details_url": plant_details_url
                }
            )

            yield TextMessage(
                    text=f"Found {len(fqids)} total matches for {plant_query.genus} {plant_query.species}. "
                         f"Retrieved detailed information for {len(plant_details)} plants. "
                         f"The artifact contains the complete botanical information."
                )

        except InstructorRetryException as e:
            yield TextMessage(text="Sorry, I couldn't extract plant information from your request.")
        except Exception as e:
            yield TextMessage(text=f"An error occurred while retrieving plant information: {str(e)}")


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
