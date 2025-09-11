from pydantic import BaseModel, Field, field_validator, AnyUrl
from organism_validator_classes import OntologyValidator
from typing import List, Optional, Union, Literal
import re

from .standard_ruleset import SampleCoreMetadata

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

class FAANGOrganismSample(SampleCoreMetadata):
    # Required organism-specific fields
    organism: str = Field(..., alias="Organism")
    organism_term_source_id: Union[str, Literal["restricted access"]] = Field(..., alias="Organism Term Source ID")
    sex: str = Field(..., alias="Sex")
    sex_term_source_id: Union[str, Literal["restricted access"]] = Field(..., alias="Sex Term Source ID")

    # Recommended fields
    birth_date: Optional[str] = Field(None, alias="Birth Date")
    birth_date_unit: Optional[Literal[
        "YYYY-MM-DD",
        "YYYY-MM",
        "YYYY",
        "not applicable",
        "not collected",
        "not provided",
        "restricted access",
        ""  # Allow empty string
    ]] = Field(None, alias="Unit")
    breed: Optional[str] = Field(None, alias="Breed")
    breed_term_source_id: Optional[Union[str, Literal["not applicable", "restricted access", ""]]] = Field(None,
                                                                                                           alias="Breed Term Source ID")

    health_status: Optional[List[HealthStatus]] = Field(None,
                                                        alias="health_status",
                                                        description="Healthy animals should have the term normal, "
                                                                    "otherwise use the as many disease terms as "
                                                                    "necessary from EFO.")
    # Optional fields - numeric fields
    diet: Optional[str] = Field(None, alias="Diet")
    birth_location: Optional[str] = Field(None, alias="Birth Location")
    birth_location_latitude: Optional[str] = Field(None, alias="Birth Location Latitude")
    birth_location_latitude_unit: Optional[Literal["decimal degrees", ""]] = Field(None,
                                                                                   alias="Birth Location Latitude Unit")
    birth_location_longitude: Optional[str] = Field(None, alias="Birth Location Longitude")
    birth_location_longitude_unit: Optional[Literal["decimal degrees", ""]] = Field(None,
                                                                                    alias="Birth Location Longitude Unit")
    birth_weight: Optional[str] = Field(None, alias="Birth Weight")
    birth_weight_unit: Optional[Literal["kilograms", "grams", ""]] = Field(None, alias="Birth Weight Unit")
    placental_weight: Optional[str] = Field(None, alias="Placental Weight")
    placental_weight_unit: Optional[Literal["kilograms", "grams", ""]] = Field(None, alias="Placental Weight Unit")
    pregnancy_length: Optional[str] = Field(None, alias="Pregnancy Length")
    pregnancy_length_unit: Optional[Literal["days", "weeks", "months", "day", "week", "month", ""]] = Field(None,
                                                                                                            alias="Pregnancy Length Unit")
    delivery_timing: Optional[Literal[
        "early parturition",
        "full-term parturition",
        "delayed parturition",
        ""  # Allow empty string
    ]] = Field(None, alias="Delivery Timing")
    delivery_ease: Optional[Literal[
        "normal autonomous delivery",
        "c-section",
        "veterinarian assisted",
        ""  # Allow empty string
    ]] = Field(None, alias="Delivery Ease")
    child_of: Optional[List[str]] = Field(None, alias="Child Of")
    pedigree: Optional[str] = Field(None,
                                    alias="Pedigree")  # Should be AnyUrl in original but keeping as string for JSON compatibility

    @field_validator('organism_term_source_id')
    def validate_organism_term(cls, v, info):
        """Validate organism term format and ontology"""
        if v == "restricted access":
            return v

        # Convert underscore format to colon format for validation
        term_with_colon = v.replace('_', ':', 1)

        if not term_with_colon.startswith("NCBITaxon:"):
            raise ValueError(f"Organism term '{v}' should be from NCBITaxon ontology")

        # Optional: Add actual ontology validation
        ov = OntologyValidator(cache_enabled=True)
        res = ov.validate_ontology_term(
            term=term_with_colon,
            ontology_name="NCBITaxon",
            allowed_classes=["NCBITaxon"]
        )
        if res.errors:
            raise ValueError(f"Organism term invalid: {res.errors}")

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

        # Optional: Add actual ontology validation
        ov = OntologyValidator(cache_enabled=True)
        res = ov.validate_ontology_term(
            term=term_with_colon,
            ontology_name="PATO",
            allowed_classes=["PATO:0000047"]
        )
        if res.errors:
            raise ValueError(f"Sex term invalid: {res.errors}")

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

        # Optional: Add actual ontology validation
        ov = OntologyValidator(cache_enabled=True)
        res = ov.validate_ontology_term(
            term=term_with_colon,
            ontology_name="LBO",
            allowed_classes=["LBO"]
        )
        if res.errors:
            raise ValueError(f"Breed term invalid: {res.errors}")

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

    @field_validator('birth_location_latitude')
    def validate_latitude(cls, v):
        """Validate latitude value if provided"""
        if not v or v.strip() == "":
            return v

        try:
            lat_val = float(v)
            if not (-90 <= lat_val <= 90):
                raise ValueError(f"Latitude must be between -90 and 90 degrees, got {lat_val}")
        except ValueError as e:
            if "could not convert" in str(e):
                raise ValueError(f"Latitude must be a valid number, got '{v}'")
            raise

        return v

    @field_validator('birth_location_longitude')
    def validate_longitude(cls, v):
        """Validate longitude value if provided"""
        if not v or v.strip() == "":
            return v

        try:
            lon_val = float(v)
            if not (-180 <= lon_val <= 180):
                raise ValueError(f"Longitude must be between -180 and 180 degrees, got {lon_val}")
        except ValueError as e:
            if "could not convert" in str(e):
                raise ValueError(f"Longitude must be a valid number, got '{v}'")
            raise

        return v

    @field_validator('birth_weight', 'placental_weight', 'pregnancy_length')
    def validate_numeric_fields(cls, v):
        """Validate numeric fields if provided"""
        if not v or v.strip() == "":
            return v

        try:
            float(v)
        except ValueError:
            field_name = cls.__name__  # This won't work as expected, but shows intent
            raise ValueError(f"Value must be a valid number, got '{v}'")

        return v

    @field_validator('child_of')
    def validate_child_of(cls, v):
        """Clean up child_of list and validate constraints"""
        if v is None:
            return None

        # Filter out empty strings and None values
        cleaned = [item.strip() for item in v if item and item.strip()]

        if len(cleaned) > 2:
            raise ValueError("Organism can have at most 2 parents")

        return cleaned if cleaned else None

    @field_validator('pedigree')
    def validate_pedigree_url(cls, v):
        """Validate pedigree URL format if provided"""
        if not v or v.strip() == "":
            return v

        # Basic URL validation (simplified since original used AnyUrl)
        if not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError("Pedigree must be a valid URL starting with http:// or https://")

        return v

    # Helper method to convert empty strings to None for optional fields
    @field_validator(
        'birth_date_unit', 'birth_location_latitude_unit', 'birth_location_longitude_unit',
        'birth_weight_unit', 'placental_weight_unit', 'pregnancy_length_unit',
        'delivery_timing', 'delivery_ease', 'diet', 'birth_location',
        'birth_location_latitude', 'birth_location_longitude', 'birth_weight',
        'placental_weight', 'pregnancy_length', 'pedigree', 'breed_term_source_id'
    )
    def convert_empty_strings_to_none(cls, v):
        """Convert empty strings to None for optional fields"""
        if v is not None and v.strip() == "":
            return None
        return v

    class Config:
        populate_by_name = True
        validate_default = True
        validate_assignment = True
        extra = "forbid"