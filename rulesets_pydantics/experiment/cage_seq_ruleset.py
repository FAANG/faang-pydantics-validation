from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal, Union
from validation.validation_utils import (
    validate_url,
    strip_and_convert_empty_to_none
)
from .core_ruleset import ExperimentCoreMetadata


class FAANGCAGESeqExperiment(ExperimentCoreMetadata):
    # required fields
    experiment_target_text: str = Field(..., alias="Experiment Target Text")
    experiment_target_term: Literal["SO:0000315", "restricted access"] = Field(
        ..., alias="Experiment Target Term")
    cage_protocol: str = Field(..., alias="CAGE Protocol")
    restriction_enzyme_target_sequence: str = Field(..., alias="Restriction Enzyme Target Sequence")
    
    # recommended fields
    sequencing_primer_provider: Optional[str] = Field(
        None, alias="Sequencing Primer Provider",
        json_schema_extra={"recommended": True})
    sequencing_primer_catalog: Optional[str] = Field(
        None, alias="Sequencing Primer Catalog",
        json_schema_extra={"recommended": True})
    sequencing_primer_lot: Optional[str] = Field(
        None, alias="Sequencing Primer Lot",
        json_schema_extra={"recommended": True}
    )
    
    rna_purity_260_280_ratio: Optional[Union[float, Literal[
        "not applicable", "not collected", "not provided", "restricted access"
    ]]] = Field(None, alias="RNA Purity 260:280 Ratio",
                json_schema_extra={"recommended": True})

    rna_purity_260_230_ratio: Optional[Union[float, Literal[
        "not applicable", "not collected", "not provided", "restricted access"
    ]]] = Field(None, alias="RNA Purity 260:230 Ratio",
                json_schema_extra={"recommended": True})
    
    rna_integrity_number: Optional[Union[float, Literal[
        "not applicable", "not collected", "not provided", "restricted access"
    ]]] = Field(None, alias="RNA Integrity Number",
                json_schema_extra={"recommended": True})
    
    # validators
    @field_validator('cage_protocol')
    def validate_protocol_url(cls, v):
        return validate_url(v, field_name="CAGE Protocol", allow_restricted=True)
    
    @field_validator('rna_purity_260_280_ratio', 'rna_purity_260_230_ratio', 'rna_integrity_number', mode='before')
    def validate_rna_quality_metrics(cls, v):
        if v in ["not applicable", "not collected", "not provided", "restricted access", None]:
            return v
        try:
            return float(v)
        except (ValueError, TypeError):
            return None
    
    @field_validator(
        'sequencing_primer_provider', 'sequencing_primer_catalog', 'sequencing_primer_lot',
        'rna_purity_260_280_ratio', 'rna_purity_260_230_ratio', 'rna_integrity_number',
        mode='before'
    )
    def convert_empty_to_none(cls, v):
        return strip_and_convert_empty_to_none(v)
    
    class Config:
        populate_by_name = True
        validate_default = True
        validate_assignment = True
        extra = "forbid"
