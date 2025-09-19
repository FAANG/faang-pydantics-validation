from pydantic import BaseModel, Field, field_validator, model_validator
from generic_validator_classes import OntologyValidator  # Assuming this exists from your organism example
from typing import List, Optional, Union, Literal
import re
from datetime import datetime

from .standard_ruleset import SampleCoreMetadata


# class MaterialField(BaseModel):
#     text: Literal[
#         "organism", "specimen from organism", "cell specimen", "single cell specimen",
#         "pool of specimens", "cell culture", "cell line", "organoid", "restricted access"
#     ]
#     term: Literal[
#         "OBI:0100026", "OBI:0001479", "OBI:0001468", "OBI:0002127",
#         "OBI:0302716", "OBI:0001876", "CLO:0000031", "NCIT:C172259", "restricted access"
#     ]
#
#     @field_validator('text')
#     def validate_material_text(cls, v, info):
#         # For organoid samples, text should be "organoid"
#         if v != "organoid" and v != "restricted access":
#             raise ValueError("Material text must be 'organoid' for organoid samples")
#         return v




class OrganModelField(BaseModel):
    text: str
    term: Union[str, Literal["restricted access"]]
    mandatory: Literal["mandatory"] = "mandatory"
    ontology_name: Literal["UBERON", "BTO"]

    @field_validator('term')
    def validate_organ_model_term(cls, v, info):
        if v == "restricted access":
            return v

        # Convert underscore to colon if needed
        term_with_colon = v.replace('_', ':', 1)

        # Validate ontology term
        ov = OntologyValidator(cache_enabled=True)
        values = info.data
        ont = values.get('ontology_name')

        # Determine allowed classes based on ontology
        if ont == "UBERON":
            allowed_classes = ["UBERON:0001062"]
        elif ont == "BTO":
            allowed_classes = ["BTO:0000042"]
        else:
            allowed_classes = ["UBERON:0001062", "BTO:0000042"]

        res = ov.validate_ontology_term(
            term=term_with_colon,
            ontology_name=ont,
            allowed_classes=allowed_classes
        )
        if res.errors:
            raise ValueError(f"Organ model term invalid: {res.errors}")

        return v


class OrganPartModelField(BaseModel):
    text: str
    term: Union[str, Literal["restricted access"]]
    mandatory: Literal["optional"] = "optional"
    ontology_name: Literal["UBERON", "BTO"]

    @field_validator('term')
    def validate_organ_part_term(cls, v, info):
        if v == "restricted access":
            return v

        term_with_colon = v.replace('_', ':', 1)
        ov = OntologyValidator(cache_enabled=True)
        values = info.data
        ont = values.get('ontology_name')

        if ont == "UBERON":
            allowed_classes = ["UBERON:0001062"]
        elif ont == "BTO":
            allowed_classes = ["BTO:0000042"]
        else:
            allowed_classes = ["UBERON:0001062", "BTO:0000042"]

        res = ov.validate_ontology_term(
            term=term_with_colon,
            ontology_name=ont,
            allowed_classes=allowed_classes
        )
        if res.errors:
            raise ValueError(f"Organ part model term invalid: {res.errors}")

        return v


class FreezingDateField(BaseModel):
    value: Union[str, Literal["restricted access"]]
    mandatory: Literal["mandatory"] = "mandatory"
    units: Literal["YYYY-MM-DD", "YYYY-MM", "YYYY", "restricted access"]

    @field_validator('value')
    def validate_freezing_date_value(cls, v, info):
        if v == "restricted access":
            return v

        values = info.data
        units = values.get('units')

        if units == "YYYY-MM-DD":
            pattern = r'^[12]\d{3}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$'
            date_format = '%Y-%m-%d'
        elif units == "YYYY-MM":
            pattern = r'^[12]\d{3}-(0[1-9]|1[0-2])$'
            date_format = '%Y-%m'
        elif units == "YYYY":
            pattern = r'^[12]\d{3}$'
            date_format = '%Y'
        else:
            return v

        if not re.match(pattern, v):
            raise ValueError(f"Invalid freezing date format: {v}. Must match {units} pattern")

        try:
            datetime.strptime(v, date_format)
        except ValueError:
            raise ValueError(f"Invalid date value: {v}")

        return v


class FreezingMethodField(BaseModel):
    value: Literal[
        "ambient temperature", "cut slide", "fresh", "frozen, -70 freezer",
        "frozen, -150 freezer", "frozen, liquid nitrogen", "frozen, vapor phase",
        "paraffin block", "RNAlater, frozen", "TRIzol, frozen"
    ]
    mandatory: Literal["mandatory"] = "mandatory"


class FreezingProtocolField(BaseModel):
    value: Union[str, Literal["restricted access"]]  # Should be URI format
    mandatory: Literal["mandatory"] = "mandatory"

    @field_validator('value')
    def validate_protocol_uri(cls, v):
        if v == "restricted access":
            return v
        if not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError("Freezing protocol must be a valid URL")
        return v


class NumberOfFrozenCellsField(BaseModel):
    value: float
    units: Literal["organoids"] = "organoids"
    mandatory: Literal["optional"] = "optional"

    @field_validator('value')
    def validate_positive_number(cls, v):
        if v < 0:
            raise ValueError("Number of frozen cells must be non-negative")
        return v


class OrganoidPassageField(BaseModel):
    value: float
    units: Literal["passages"] = "passages"
    mandatory: Literal["mandatory"] = "mandatory"

    @field_validator('value')
    def validate_passage_number(cls, v):
        if v < 0:
            raise ValueError("Organoid passage must be non-negative")
        return v


class OrganoidPassageProtocolField(BaseModel):
    value: Union[str, Literal["restricted access"]]
    mandatory: Literal["mandatory"] = "mandatory"

    @field_validator('value')
    def validate_protocol_uri(cls, v):
        if v == "restricted access":
            return v
        if not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError("Organoid passage protocol must be a valid URL")
        return v


class OrganoidCulturePassageProtocolField(BaseModel):
    value: Union[str, Literal["restricted access"]]
    mandatory: Literal["mandatory"] = "mandatory"

    @field_validator('value')
    def validate_protocol_uri(cls, v):
        if v == "restricted access":
            return v
        if not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError("Organoid culture and passage protocol must be a valid URL")
        return v


class GrowthEnvironmentField(BaseModel):
    value: Literal["matrigel", "liquid suspension", "adherent"]
    mandatory: Literal["mandatory"] = "mandatory"


class TypeOfOrganoidCultureField(BaseModel):
    value: Literal["2D", "3D"]
    mandatory: Literal["mandatory"] = "mandatory"


class OrganoidMorphologyField(BaseModel):
    value: str
    mandatory: Literal["optional"] = "optional"


class DerivedFromField(BaseModel):
    value: str
    mandatory: Literal["mandatory"] = "mandatory"

    @field_validator('value')
    def validate_derived_from_value(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Derived from value is required and cannot be empty")
        return v.strip()


class FAANGOrganoidSample(SampleCoreMetadata):


    # Required core fields
    # material: MaterialField # koosum to check material text should be organoid



    # Required organoid-specific fields
    sample_name: str = Field(..., alias="Sample Name")
    organ_model: OrganModelField
    freezing_method: FreezingMethodField
    organoid_passage: OrganoidPassageField
    organoid_passage_protocol: OrganoidPassageProtocolField
    type_of_organoid_culture: TypeOfOrganoidCultureField
    growth_environment: GrowthEnvironmentField
    derived_from: DerivedFromField

    # Conditional fields (required if freezing_method != "fresh")
    freezing_date: Optional[FreezingDateField] = None
    freezing_protocol: Optional[FreezingProtocolField] = None

    # Optional organoid fields
    organ_part_model: Optional[OrganPartModelField] = None
    number_of_frozen_cells: Optional[NumberOfFrozenCellsField] = None
    organoid_culture_and_passage_protocol: Optional[OrganoidCulturePassageProtocolField] = None
    organoid_morphology: Optional[OrganoidMorphologyField] = None



    @model_validator(mode='after')
    def validate_conditional_requirements(self):
        """Implement the allOf conditional logic from JSON schema"""
        freezing_method_value = self.freezing_method.value if self.freezing_method else None

        if freezing_method_value and freezing_method_value != "fresh":
            # If freezing method is not "fresh", freezing_date and freezing_protocol are required
            if not self.freezing_date:
                raise ValueError("Freezing date is required when freezing method is not 'fresh'")
            if not self.freezing_protocol:
                raise ValueError("Freezing protocol is required when freezing method is not 'fresh'")

        return self

    class Config:
        populate_by_name = True
        validate_default = True
        validate_assignment = True
        extra = "forbid"