from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal, Union
from validation.validation_utils import (
    validate_url,
    validate_non_negative_numeric,
    strip_and_convert_empty_to_none
)
from validation.generic_validator_classes import get_ontology_validator
from validation.validation_utils import normalize_ontology_term
from .core_ruleset import ExperimentCoreMetadata


class FAANGChIPSeqExperiment(ExperimentCoreMetadata):
    # required fields
    experiment_target_text: str = Field(..., alias="Experiment Target")
    experiment_target_term_source_id: Literal[
        "SO:0001700",  # TF_binding_site
        "SO:0000235",  # histone_modification
        "EFO:0005031",  # input DNA
        "restricted access"
    ] = Field(..., alias="Experiment Target Term Source ID")

    chip_protocol: str = Field(..., alias="ChIP Protocol")

    # optional
    adapter_step: Optional[Literal[
        "Tn5 tagmentation",
        "Ligation",
        "restricted access"
    ]] = Field(..., alias="Adapter Step")

    # Validators
    @field_validator('chip_protocol')
    def validate_chip_protocol_url(cls, v):
        return validate_url(v, field_name="ChIP Protocol", allow_restricted=True)

    @field_validator('adapter_step', mode='before')
    def convert_empty_to_none(cls, v):
        return strip_and_convert_empty_to_none(v)

    class Config:
        populate_by_name = True
        validate_default = True
        validate_assignment = True
        extra = "forbid"


class FAANGChIPSeqDNABindingProteinsExperiment(FAANGChIPSeqExperiment):
    # required fields
    chip_target_text: str = Field(..., alias="ChIP Target")
    chip_target_term_source_id: str = Field(..., alias="ChIP Target Term Source ID")

    chip_antibody_provider: str = Field(..., alias="ChIP Antibody Provider")
    chip_antibody_catalog: str = Field(..., alias="ChIP Antibody Catalog")
    chip_antibody_lot: str = Field(..., alias="ChIP Antibody Lot")

    library_generation_max_fragment_size_range: float = Field(..., alias="Library Generation Max Fragment Size Range")
    library_generation_min_fragment_size_range: float = Field(..., alias="Library Generation Min Fragment Size Range")

    # Recommended fields
    control_experiment: Optional[str] = Field(
        None, alias="Control Experiment",
        json_schema_extra={"recommended": True}
    )

    # Validators
    @field_validator('chip_target_term')
    def validate_chip_target_term(cls, v, info):
        if v == "restricted access":
            return v

        # term can be from CHEBI, OMIT, or NCIT
        ov = get_ontology_validator()

        allowed_classes = ["OMIT:0038500", "NCIT:C17804", "NCIT:C34071"]
        if v in allowed_classes:
            return v

        # otherwise validate as CHEBI term (subclass of CHEBI:15358 - histone)
        term = normalize_ontology_term(v)
        if term.startswith("CHEBI:"):
            res = ov.validate_ontology_term(
                term=term,
                ontology_name="CHEBI",
                allowed_classes=["CHEBI:15358"],
                text=info.data.get('chip_target_text'),
                field_name='chip_target_text'
            )
            if res.errors:
                raise ValueError(f"ChIP target term invalid: {res.errors}")

        return v

    @field_validator('library_generation_max_fragment_size_range', 'library_generation_min_fragment_size_range', mode='before')
    def validate_fragment_size(cls, v):
        if v == "restricted access":
            return v
        return validate_non_negative_numeric(v, "Fragment size", allow_restricted=True)

    @field_validator('control_experiment', mode='before')
    def convert_empty_to_none(cls, v):
        return strip_and_convert_empty_to_none(v)

    class Config:
        populate_by_name = True
        validate_default = True
        validate_assignment = True
        extra = "forbid"


class FAANGChIPSeqInputDNAExperiment(FAANGChIPSeqExperiment):
    # required fields
    library_generation_max_fragment_size_range: (
        Union)[float, Literal["restricted access"]] = Field(..., alias="Library Generation Max Fragment Size Range")

    library_generation_min_fragment_size_range: (
        Union)[float, Literal["restricted access"]] = Field(..., alias="Library Generation Min Fragment Size Range")

    # validators
    @field_validator('library_generation_max_fragment_size_range', 'library_generation_min_fragment_size_range', mode='before')
    def validate_fragment_size(cls, v):
        return validate_non_negative_numeric(v, "Fragment size", allow_restricted=True)

    class Config:
        populate_by_name = True
        validate_default = True
        validate_assignment = True
        extra = "forbid"
