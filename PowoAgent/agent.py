import os
from typing import Optional, AsyncGenerator, List, Dict, Any
from pydantic import BaseModel, Field
from ichatbio.agent import IChatBioAgent
from ichatbio.types import AgentCard, AgentEntrypoint, ProcessMessage, TextMessage, Message
from openai import AsyncOpenAI
import instructor
import pykew.powo as powo
from pykew.powo_terms import Name, Filters

# ---------- Models ----------

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

class PlantDataParameters(BaseModel):
    genus: str = Field(..., description="Genus of the plant, e.g Mangifera")
    species: str = Field(..., description="Species of the plant, e.g indica")

class POWOAgent(IChatBioAgent):
    def __init__(self):
        self.agent_card = AgentCard(
            name="POWO Plant Data Agent",
            description="Fetches plant data from POWO database from the given genus and species.",
            icon=None,
            entrypoints=[
                AgentEntrypoint(
                    id="get_plant_data",
                    description="Get plant data using structured genus and species input.",
                    parameters=PlantDataParameters
                )
            ]
        )

    def get_agent_card(self) -> AgentCard:
        return self.agent_card

    async def run(self, request: str, entrypoint: str, params: Optional[BaseModel]) -> AsyncGenerator[None, Message]:
        # openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # instructor_client = instructor.patch(openai_client)

        try:
            if entrypoint != "chat":
                raise ValueError()

            yield ProcessMessage(summary="Searching POWO", description=f"Genus: {params.genus}, Species: {params.species}")

            query = {Name.genus: params.genus, Name.species: params.species}
            res = powo.search(query, filters=[Filters.species])
            species = [Plant(**entry) for entry in res]
            fqids = [plant.fqId for plant in species]

            if not fqids:
                yield TextMessage(text="No plant data found for that genus and species.")
                return

            yield ProcessMessage(summary="Fetching detailed data", description=f"Found {len(fqids)} result(s)")

            species_details = [powo.lookup(fqid) for fqid in fqids]
            plant_data = [PlantData(**data) for data in species_details]

            for plant in plant_data:
                yield TextMessage(text=(plant))

        except Exception as e:
            yield TextMessage(text=f" Error: {str(e)}")