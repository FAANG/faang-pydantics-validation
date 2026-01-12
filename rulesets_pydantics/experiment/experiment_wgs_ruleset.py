from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal, Union
from app.validation.validation_utils import (
    validate_url,
    strip_and_convert_empty_to_none
)
from .experiment_core_ruleset import ExperimentCoreMetadata


class FAANGWGSExperiment(ExperimentCoreMetadata):
    """Whole Genome Sequencing (WGS) experiment metadata model."""
    
    # Required fields
    experiment_target_text: Union[str, Literal["restricted access"]] = Field(
        ..., alias="Experiment Target Text"
    )
    experiment_target_term: Literal["EFO:0005031", "restricted access"] = Field(
        ..., alias="Experiment Target Term"
    )
    
    library_generation_pcr_product_isolation_protocol: str = Field(
        ..., alias="Library Generation PCR Product Isolation Protocol"
    )
    library_generation_protocol: str = Field(
        ..., alias="Library Generation Protocol"
    )
    
    # Optional fields
    library_selection: Optional[Literal[
        "reduced representation",
        "none"
    ]] = Field(None, alias="Library Selection")
    
    # Validators
    @field_validator('experiment_target_term')
    def validate_target_term(cls, v):
        # For WGS, the term should be 'input DNA' (EFO:0005031)
        if v not in ["EFO:0005031", "restricted access"]:
            raise ValueError("For WGS, experiment target term must be 'EFO:0005031' (input DNA)")
        return v
    
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
