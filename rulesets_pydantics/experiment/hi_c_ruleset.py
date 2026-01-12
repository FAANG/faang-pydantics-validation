from pydantic import BaseModel, Field, field_validator
from typing import Literal
from validation.validation_utils import validate_url
from .core_ruleset import ExperimentCoreMetadata


class FAANGHiCExperiment(ExperimentCoreMetadata):
    # required fields
    experiment_target_text: str = Field(..., alias="Experiment Target Text")
    experiment_target_term: Literal["GO:0000785", "restricted access"] = Field(
        ..., alias="Experiment Target Term")
    restriction_enzyme: str = Field(..., alias="Restriction Enzyme")
    restriction_site: str = Field(..., alias="Restriction Site")
    hi_c_protocol: str = Field(..., alias="Hi-C Protocol")
    
    # validators
    @field_validator('hi_c_protocol')
    def validate_protocol_url(cls, v):
        return validate_url(v, field_name="Hi-C Protocol", allow_restricted=True)
    
    class Config:
        populate_by_name = True
        validate_default = True
        validate_assignment = True
        extra = "forbid"
