from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal, Union
from validation.validation_utils import (
    validate_url,
    strip_and_convert_empty_to_none
)
from .core_ruleset import ExperimentCoreMetadata


class FAANGWGSExperiment(ExperimentCoreMetadata):
    # required fields
    experiment_target_text: Union[str, Literal["restricted access"]] = Field(
        ..., alias="Experiment Target")
    experiment_target_term: Literal["EFO:0005031", "restricted access"] = Field(
        ..., alias="Experiment Target Term")
    
    library_generation_pcr_product_isolation_protocol: str = Field(
        ..., alias="Library Generation PCR Product Isolation Protocol")
    library_generation_protocol: str = Field(..., alias="Library Generation Protocol")
    
    # optional fields
    library_selection: Optional[Literal[
        "reduced representation",
        "none"
    ]] = Field(None, alias="Library Selection")
    
    # validators
    @field_validator(
        'library_generation_pcr_product_isolation_protocol',
        'library_generation_protocol'
    )
    def validate_protocol_urls(cls, v):
        return validate_url(v, field_name="Protocol", allow_restricted=True)
    
    @field_validator('library_selection', mode='before')
    def convert_empty_to_none(cls, v):
        return strip_and_convert_empty_to_none(v)
    
    class Config:
        populate_by_name = True
        validate_default = True
        validate_assignment = True
        extra = "forbid"
