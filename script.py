import pykew.powo as powo
from pykew.powo_terms import Name, Filters
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sys

# General Plat Model
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

genus_input = sys.argv[1]
species_input = sys.argv[2]

query = { Name.genus: genus_input, Name.species: species_input}
res = powo.search(query, filters = [Filters.species])

species = [Plant(**entry) for entry in res ]
fqids = [plant.fqId for plant in species]

species_details = [ powo.lookup(ids) for ids in fqids ]
plant_data = [PlantData(**data) for data in species_details]

print(plant_data)
