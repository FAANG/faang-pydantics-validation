from pydantic import BaseModel, Field, field_validator
from typing import Literal
from validation.validation_utils import validate_url
from .core_ruleset import ExperimentCoreMetadata


class FAANGDNaseSeqExperiment(ExperimentCoreMetadata):
    # required fields
    experiment_target_text: str = Field(..., alias="Experiment Target Text")
    experiment_target_term: Literal["SO:0001747", "restricted access"] = Field(..., alias="Experiment Target Term")
    
    dnase_protocol: str = Field(..., alias="DNase Protocol")
    
    # Validators
    @field_validator('experiment_target_term')
    def validate_target_term(cls, v):
        if v not in ["SO:0001747", "restricted access"]:
            raise ValueError("For DNase-seq, experiment target term must be 'SO:0001747' (open_chromatin_region) or 'restricted access'")
        return v
    
    @field_validator('dnase_protocol')
    def validate_protocol_url(cls, v):
        return validate_url(v, field_name="DNase Protocol", allow_restricted=True)
    
    class Config:
        populate_by_name = True
        validate_default = True
        validate_assignment = True
        extra = "forbid"
