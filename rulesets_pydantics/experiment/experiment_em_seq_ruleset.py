from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal, Union
from validation.validation_utils import (
    validate_url,
    validate_non_negative_numeric,
    strip_and_convert_empty_to_none
)
from .core_ruleset import ExperimentCoreMetadata


class FAANGEMSeqExperiment(ExperimentCoreMetadata):
    # required fields
    experiment_target_text: str = Field(..., alias="Experiment Target Text")
    experiment_target_term: Literal["GO:0006306", "restricted access"] = Field(..., alias="Experiment Target Term")
    
    library_selection: Literal[
        "whole-genome",
        "selected genomic regions",
        "restricted access"
    ] = Field(..., alias="Library Selection")
    
    max_fragment_size_selection_range: Union[float, Literal[
        "not applicable", "not collected", "not provided", "restricted access"
    ]] = Field(..., alias="Max Fragment Size Selection Range") # tocheck - might be recommended
    
    min_fragment_size_selection_range: Union[float, Literal[
        "not applicable", "not collected", "not provided", "restricted access"
    ]] = Field(..., alias="Min Fragment Size Selection Range") # tocheck - might be recommended
    
    enzymatic_methylation_conversion_protocol: str = Field(..., alias="Enzymatic Methylation Conversion Protocol")
    
    # recommended fields
    enzymatic_methylation_conversion_percent: Optional[Union[float, Literal[
        "not applicable", "not collected", "not provided", "restricted access"
    ]]] = Field(None, alias="Enzymatic Methylation Conversion Percent",
                json_schema_extra={"recommended": True})
    
    # validators
    @field_validator('enzymatic_methylation_conversion_protocol')
    def validate_protocol_url(cls, v):
        return validate_url(v, field_name="Enzymatic Methylation Conversion Protocol", allow_restricted=True)
    
    @field_validator('max_fragment_size_selection_range', 'min_fragment_size_selection_range', mode='before')
    def validate_fragment_size(cls, v):
        if v in ["not applicable", "not collected", "not provided", "restricted access"]:
            return v
        return validate_non_negative_numeric(v, "Fragment size", allow_restricted=False)
    
    @field_validator('enzymatic_methylation_conversion_percent', mode='before')
    def validate_conversion_percent(cls, v):
        if v in ["not applicable", "not collected", "not provided", "restricted access", None]:
            return v
        try:
            val = float(v)
            if val < 0 or val > 100:
                raise ValueError("Enzymatic methylation conversion percent must be between 0 and 100")
            return val
        except (ValueError, TypeError):
            return None
    
    @field_validator('enzymatic_methylation_conversion_percent', mode='before')
    def convert_empty_to_none(cls, v):
        return strip_and_convert_empty_to_none(v)
    
    class Config:
        populate_by_name = True
        validate_default = True
        validate_assignment = True
        extra = "forbid"
