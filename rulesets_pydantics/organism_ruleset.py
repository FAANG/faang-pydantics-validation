from pydantic import BaseModel, Field, field_validator, AnyUrl
from organism_validator_classes import OntologyValidator
from typing import List, Optional, Union, Literal, Dict, Any
import re

from .standard_ruleset import SampleCoreMetadata


class Organism(BaseModel):
    text: str
    term: Union[str, Literal["restricted access"]]
    ontology_name: Literal["NCBITaxon"] = "NCBITaxon"

    @field_validator('term')
    def validate_ncbi_taxon(cls, v, info):
        if v == "restricted access":
            return v

        ov = OntologyValidator(cache_enabled=True)
        values = info.data
        ont = values.get('ontology_name', "NCBITaxon")
        res = ov.validate_ontology_term(
            term=v,
            ontology_name=ont,
            allowed_classes=["NCBITaxon"]
        )
        if res.errors:
            raise ValueError(f"Organism term invalid: {res.errors}")
        return v


class Sex(BaseModel):
    text: str
    ontology_name: Literal["PATO"] = "PATO"
    term: Union[str, Literal["restricted access"]]

    @field_validator('term')
    def validate_pato_sex(cls, v, info):
        if v == "restricted access":
            return v

        ov = OntologyValidator(cache_enabled=True)
        values = info.data
        ont = values.get('ontology_name')
        res = ov.validate_ontology_term(
            term=v,
            ontology_name=ont,
            allowed_classes=["PATO:0000047"]
        )
        if res.errors:
            raise ValueError(f"Sex term invalid: {res.errors}")
        return v


class BirthDate(BaseModel):
    value: str
    units: Literal[
    "YYYY-MM-DD",
    "YYYY-MM",
    "YYYY",
    "not applicable",
    "not collected",
    "not provided",
    "restricted access"
]

    @field_validator('value')
    def validate_birth_date(cls, v, info):
        if v in ["not applicable", "not collected", "not provided", "restricted access"]:
            return v

        pattern = r'^[12]\d{3}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])|[12]\d{3}-(0[1-9]|1[0-2])|[12]\d{3}$'

        if not re.match(pattern, v):
            raise ValueError(f"Invalid birth date format: {v}. Must match YYYY-MM-DD, YYYY-MM, or YYYY pattern")

        return v


class Breed(BaseModel):
    text: str
    ontology_name: Literal["LBO"] = "LBO"
    term: Union[str, Literal["not applicable", "restricted access"]]

    @field_validator('term')
    def validate_lbo_breed(cls, v, info):
        if v in ["not applicable", "restricted access"]:
            return v

        ov = OntologyValidator(cache_enabled=True)
        values = info.data
        ont = values.get('ontology_name')
        res = ov.validate_ontology_term(
            term=v,
            ontology_name=ont,
            allowed_classes=["LBO"]
        )
        if res.errors:
            raise ValueError(f"Breed term invalid: {res.errors}")

        return v


class HealthStatus(BaseModel):
    text: str
    ontology_name: Optional[Literal["PATO", "EFO"]] = None
    term: Union[str, Literal["not applicable", "not collected", "not provided", "restricted access"]]

    @field_validator('term')
    def validate_health_status(cls, v, info):
        if v in ["not applicable", "not collected", "not provided", "restricted access"]:
            return v

        # determine which ontology to use (PATO or EFO)
        ov = OntologyValidator(cache_enabled=True)
        values = info.data
        ont = values.get('ontology_name', "PATO")
        res = ov.validate_ontology_term(
            term=v,
            ontology_name=ont,
            allowed_classes=["PATO:0000461", "EFO:0000408"]
        )
        if res.errors:
            raise ValueError(f"HealthStatus term invalid: {res.errors}")

        return v


class Diet(BaseModel):
    value: str


class BirthLocation(BaseModel):
    value: str


class BirthLocationLatitude(BaseModel):
    value: float
    units: Literal["decimal degrees"] = "decimal degrees"


class BirthLocationLongitude(BaseModel):
    value: float
    units: Literal["decimal degrees"] = "decimal degrees"


class BirthWeight(BaseModel):
    value: float
    units: Literal["kilograms", "grams"]


class PlacentalWeight(BaseModel):
    value: float
    units: Literal["kilograms", "grams"]


class PregnancyLength(BaseModel):
    value: float
    units: Literal[
    "days",
    "weeks",
    "months",
    "day",
    "week",
    "month"
]


class DeliveryTimingField(BaseModel):
    value: Literal[
    "early parturition",
    "full-term parturition",
    "delayed parturition"
]


class DeliveryEaseField(BaseModel):
    value: Literal[
    "normal autonomous delivery",
    "c-section",
    "veterinarian assisted"
]


class Pedigree(BaseModel):
    value: AnyUrl


class ChildOf(BaseModel):
    value: str


class SampleName(BaseModel):
    value: str


class Custom(BaseModel):
    sample_name: SampleName


class FAANGOrganismSample(BaseModel):
    organism: List[Dict[str, Any]] = Field(..., description="List of organism samples")

    class Config:
        extra = "forbid"
        validate_by_name = True
        validate_default = True
        validate_assignment = True

    @field_validator('organism')
    def validate_organism_samples(cls, v):
        if not v or not isinstance(v, list):
            raise ValueError("organism must be a non-empty list")

        for sample in v:
            # Validate required fields
            if "Sample Name" not in sample:
                raise ValueError("Each organism sample must have a 'Sample Name'")
            if "Material" not in sample:
                raise ValueError("Each organism sample must have a 'Material'")
            if "Term Source ID" not in sample:
                raise ValueError("Each organism sample must have a 'Material Term Source ID'")
            if "Project" not in sample:
                raise ValueError("Each organism sample must have a 'Project'")
            if "Organism" not in sample:
                raise ValueError("Each organism sample must have an 'Organism'")
            if "Organism Term Source ID" not in sample:
                raise ValueError("Each organism sample must have an 'Organism Term Source ID'")
            if "Sex" not in sample:
                raise ValueError("Each organism sample must have a 'Sex'")
            if "Sex Term Source ID" not in sample:
                raise ValueError("Each organism sample must have a 'Sex Term Source ID'")

            # Validate material
            if sample["Material"] != "organism":
                raise ValueError(f"Material must be 'organism', got '{sample['Material']}'")

            # Validate project
            if sample["Project"] != "FAANG":
                raise ValueError(f"Project must be 'FAANG', got '{sample['Project']}'")

            # Validate secondary project is a list
            if "Secondary Project" in sample and not isinstance(sample["Secondary Project"], list):
                raise ValueError("Secondary Project must be a list")

            # Validate health status is a list
            if "Health Status" in sample and not isinstance(sample["Health Status"], list):
                raise ValueError("Health Status must be a list")

            # Validate child of is a list
            if "Child Of" in sample and not isinstance(sample["Child Of"], list):
                raise ValueError("Child Of must be a list")

        return v
