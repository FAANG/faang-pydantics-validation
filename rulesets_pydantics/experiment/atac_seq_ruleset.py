from pydantic import BaseModel, Field, field_validator
from typing import Literal, Union
from validation.validation_utils import validate_url
from .core_ruleset import ExperimentCoreMetadata


class FAANGATACSeqExperiment(ExperimentCoreMetadata):
    # required fields
    experiment_target_text: str = Field(..., alias="Experiment Target")
    experiment_target_term_source_id: Literal["SO:0001747", "restricted access"] = Field(
        ..., alias="Experiment Target Term Source ID")
    transposase_protocol: str = Field(..., alias="Transposase Protocol")
    
    # Validators
    @field_validator('experiment_target_text')
    def validate_target_text(cls, v):
        if v and v.strip():
            return v
        raise ValueError("Experiment target text is required")
    
    @field_validator('experiment_target_term')
    def validate_target_term(cls, v, info):
        values = info.data

        # SO:0001747 is for open_chromatin_region
        if v not in ["SO:0001747", "restricted access"]:
            raise ValueError(f"Experiment target term must be 'SO:0001747' or 'restricted access'")

        return v
    
    @field_validator('transposase_protocol')
    def validate_transposase_protocol_url(cls, v):
        return validate_url(v, field_name="Transposase Protocol", allow_restricted=True)
    
    class Config:
        populate_by_name = True
        validate_default = True
        validate_assignment = True
        extra = "forbid"
