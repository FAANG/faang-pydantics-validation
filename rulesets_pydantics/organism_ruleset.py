from pydantic import BaseModel, Field, field_validator, AnyUrl
from organism_validator_classes import OntologyValidator
from typing import List, Optional, Union, Literal
import re

from .standard_ruleset import SampleCoreMetadata


class FAANGOrganismSample(SampleCoreMetadata):
    # Required organism-specific fields
    organism: str = Field(..., alias="Organism")
    organism_term_source_id: str = Field(..., alias="Organism Term Source ID")
    sex: str = Field(..., alias="Sex")
    sex_term_source_id: str = Field(..., alias="Sex Term Source ID")

    # Recommended fields
    birth_date: Optional[str] = Field(None, alias="Birth Date")
    birth_date_unit: Optional[str] = Field(None, alias="Unit")
    breed: Optional[str] = Field(None, alias="Breed")
    breed_term_source_id: Optional[str] = Field(None, alias="Breed Term Source ID")
    health_status: Optional[List[dict]] = Field(None, alias="health_status")  # Keep as is for now

    # Optional fields
    diet: Optional[str] = Field(None, alias="Diet")
    birth_location: Optional[str] = Field(None, alias="Birth Location")
    birth_location_latitude: Optional[str] = Field(None, alias="Birth Location Latitude")
    birth_location_latitude_unit: Optional[str] = Field(None, alias="Birth Location Latitude Unit")
    birth_location_longitude: Optional[str] = Field(None, alias="Birth Location Longitude")
    birth_location_longitude_unit: Optional[str] = Field(None, alias="Birth Location Longitude Unit")
    birth_weight: Optional[str] = Field(None, alias="Birth Weight")
    birth_weight_unit: Optional[str] = Field(None, alias="Birth Weight Unit")
    placental_weight: Optional[str] = Field(None, alias="Placental Weight")
    placental_weight_unit: Optional[str] = Field(None, alias="Placental Weight Unit")
    pregnancy_length: Optional[str] = Field(None, alias="Pregnancy Length")
    pregnancy_length_unit: Optional[str] = Field(None, alias="Pregnancy Length Unit")
    delivery_timing: Optional[str] = Field(None, alias="Delivery Timing")
    delivery_ease: Optional[str] = Field(None, alias="Delivery Ease")
    child_of: Optional[List[str]] = Field(None, alias="Child Of")
    pedigree: Optional[str] = Field(None, alias="Pedigree")

    @field_validator('organism_term_source_id')
    def validate_organism_term(cls, v, info):
        """Validate organism term format and ontology"""
        if v == "restricted access":
            return v

        # Convert underscore format to colon format for validation
        term_with_colon = v.replace('_', ':', 1)

        if not term_with_colon.startswith("NCBITaxon:"):
            raise ValueError(f"Organism term '{v}' should be from NCBITaxon ontology")

        # Here you could add actual ontology validation
        # ov = OntologyValidator(cache_enabled=True)
        # res = ov.validate_ontology_term(term=term_with_colon, ontology_name="NCBITaxon")

        return v

    @field_validator('sex_term_source_id')
    def validate_sex_term(cls, v, info):
        """Validate sex term format and ontology"""
        if v == "restricted access":
            return v

        # Convert underscore format to colon format for validation
        term_with_colon = v.replace('_', ':', 1)

        if not term_with_colon.startswith("PATO:"):
            raise ValueError(f"Sex term '{v}' should be from PATO ontology")

        return v

    @field_validator('breed_term_source_id')
    def validate_breed_term(cls, v, info):
        """Validate breed term format if provided"""
        if not v or v in ["not applicable", "restricted access", ""]:
            return v

        # Convert underscore format to colon format for validation
        term_with_colon = v.replace('_', ':', 1)

        if not term_with_colon.startswith("LBO:"):
            raise ValueError(f"Breed term '{v}' should be from LBO ontology")

        return v

    @field_validator('birth_date')
    def validate_birth_date_format(cls, v, info):
        """Validate birth date format"""
        if not v or v in ["not applicable", "not collected", "not provided", "restricted access", ""]:
            return v

        # Check format based on the unit
        values = info.data
        unit = values.get('Unit') or values.get('birth_date_unit')

        if unit == "YYYY-MM-DD":
            pattern = r'^[12]\d{3}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$'
        elif unit == "YYYY-MM":
            pattern = r'^[12]\d{3}-(0[1-9]|1[0-2])$'
        elif unit == "YYYY":
            pattern = r'^[12]\d{3}$'
        else:
            return v  # No validation if unit is not recognized

        if not re.match(pattern, v):
            raise ValueError(f"Invalid birth date format: {v}. Must match {unit} pattern")

        return v

    @field_validator('child_of')
    def validate_child_of(cls, v):
        """Clean up child_of list by removing empty strings"""
        if v is None:
            return None

        # Filter out empty strings and None values
        cleaned = [item for item in v if item and item.strip()]

        if len(cleaned) > 2:
            raise ValueError("Organism can have at most 2 parents")

        return cleaned if cleaned else None

    class Config:
        populate_by_name = True
        validate_default = True
        validate_assignment = True
        extra = "forbid"