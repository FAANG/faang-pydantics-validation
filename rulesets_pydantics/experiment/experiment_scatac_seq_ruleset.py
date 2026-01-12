from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from app.validation.validation_utils import (
    validate_url,
    strip_and_convert_empty_to_none
)
from .experiment_core_ruleset import ExperimentCoreMetadata


class FAANGscATACSeqExperiment(ExperimentCoreMetadata):
    """Single cell ATAC-seq (scATAC-seq) experiment metadata model."""
    
    # Required fields
    experiment_target_text: str = Field(..., alias="Experiment Target Text")
    experiment_target_term: Literal["SO:0001747", "restricted access"] = Field(
        ..., alias="Experiment Target Term"
    )
    
    transposase_protocol: str = Field(..., alias="Transposase Protocol")
    
    transposed_dna_sequence_file_read_index: Literal["R1/R3", "restricted access"] = Field(
        ..., alias="Transposed DNA Sequence File Read Index"
    )
    
    cell_barcode_read: Literal["R2", "restricted access"] = Field(
        ..., alias="Cell Barcode Read"
    )
    
    sample_index_read: Literal["I1", "restricted access"] = Field(
        ..., alias="Sample Index Read"
    )
    
    # Optional fields
    nuclei_acid_molecule: Optional[str] = Field(None, alias="Nuclei Acid Molecule")
    nucleic_acid_source: Optional[str] = Field(None, alias="Nucleic Acid Source")
    sequencing_method: Optional[str] = Field(None, alias="Sequencing Method")
    kit_retail_name: Optional[str] = Field(None, alias="Kit Retail Name")
    kit_manufacturer: Optional[str] = Field(None, alias="Kit Manufacturer")
    sequencing_protocol: Optional[str] = Field(None, alias="Sequencing Protocol")
    library_construction_method: Optional[str] = Field(None, alias="Library Construction Method")
    
    # Validators
    @field_validator('experiment_target_term')
    def validate_target_term(cls, v):
        # For scATAC-seq, the term should be 'open_chromatin_region' (SO:0001747)
        if v not in ["SO:0001747", "restricted access"]:
            raise ValueError("For scATAC-seq, experiment target term must be 'SO:0001747' (open_chromatin_region)")
        return v
    
    @field_validator('transposase_protocol')
    def validate_transposase_protocol_url(cls, v):
        return validate_url(v, field_name="Transposase Protocol", allow_restricted=True)
    
    @field_validator(
        'nuclei_acid_molecule', 'nucleic_acid_source', 'sequencing_method',
        'kit_retail_name', 'kit_manufacturer', 'sequencing_protocol',
        'library_construction_method', mode='before'
    )
    def convert_empty_to_none(cls, v):
        return strip_and_convert_empty_to_none(v)
    
    class Config:
        populate_by_name = True
        validate_default = True
        validate_assignment = True
        extra = "forbid"
