from pydantic import BaseModel, Field, field_validator
from typing import Optional, Union, Literal
from rulesets_pydantics.specimen_ruleset import FAANGSpecimenFromOrganismSample


class FAANGTeleosteiEmbryoSample(FAANGSpecimenFromOrganismSample):
    # required fields
    origin: Literal[
        "Domesticated diploid",
        "Domesticated Double-haploid",
        "Domesticated Isogenic",
        "Wild",
        "restricted access"
    ] = Field(..., alias="Origin")

    reproductive_strategy: Literal[
        "gonochoric",
        "simultaneous hermaphrodite",
        "successive hermaphrodite",
        "restricted access"
    ] = Field(..., alias="Reproductive Strategy")

    hatching: Literal["pre", "post", "restricted access"] = Field(..., alias="Hatching")

    time_post_fertilisation: Union[float, Literal["restricted access"]] = Field(
        ..., alias="Time Post Fertilisation"
    )
    time_post_fertilisation_unit: Literal[
        "hours", "days", "months", "years", "restricted access"
    ] = Field(..., alias="Time Post Fertilisation Unit")

    pre_hatching_water_temperature_average: Union[float, Literal["restricted access"]] = Field(
        ..., alias="Pre-hatching Water Temperature Average"
    )
    pre_hatching_water_temperature_average_unit: Literal[
        "Degrees celsius", "restricted access"
    ] = Field(..., alias="Pre-hatching Water Temperature Average Unit")

    post_hatching_water_temperature_average: Union[float, Literal["restricted access"]] = Field(
        ..., alias="Post-hatching Water Temperature Average"
    )
    post_hatching_water_temperature_average_unit: Literal[
        "Degrees celsius", "restricted access"
    ] = Field(..., alias="Post-hatching Water Temperature Average Unit")

    degree_days: Union[float, Literal["restricted access"]] = Field(..., alias="Degree Days")
    degree_days_unit: Literal["Thermal time", "restricted access"] = Field(
        ..., alias="Degree Days Unit"
    )

    growth_media: Literal["Water", "Growing medium", "restricted access"] = Field(
        ..., alias="Growth Media"
    )

    medium_replacement_frequency: Union[float, Literal["restricted access"]] = Field(
        ..., alias="Medium Replacement Frequency"
    )
    medium_replacement_frequency_unit: Literal["days", "restricted access"] = Field(
        ..., alias="Medium Replacement Frequency Unit"
    )

    percentage_total_somite_number: Union[float, Literal["restricted access"]] = Field(
        ..., alias="Percentage Total Somite Number"
    )
    percentage_total_somite_number_unit: Literal["%", "restricted access"] = Field(
        ..., alias="Percentage Total Somite Number Unit"
    )

    average_water_salinity: Union[float, Literal["restricted access"]] = Field(
        ..., alias="Average Water Salinity"
    )
    average_water_salinity_unit: Literal["parts per thousand", "restricted access"] = Field(
        ..., alias="Average Water Salinity Unit"
    )

    photoperiod: Union[str, Literal["natural light", "restricted access"]] = Field(
        ..., alias="Photoperiod"
    )

    # Optional/recommended field
    generations_from_wild: Optional[Union[float, Literal[
        "not applicable", "not collected", "not provided", "restricted access"
    ]]] = Field(None, alias="Generations From Wild", json_schema_extra={"recommended": True})

    generations_from_wild_unit: Optional[Literal[
        "generations from wild",
        "not applicable",
        "not collected",
        "not provided",
        "restricted access"
    ]] = Field(None, alias="Generations From Wild Unit", json_schema_extra={"recommended": True})

    # Validators
    @field_validator('photoperiod')
    def validate_photoperiod(cls, v):
        if v in ["natural light", "restricted access"]:
            return v

        # Pattern: e.g., "12L:12D" (light:dark ratio)
        import re
        pattern = r'^(2[0-4]|1[0-9]|[1-9])L:(2[0-4]|1[0-9]|[1-9])D$'
        if not re.match(pattern, v):
            raise ValueError(
                f"Photoperiod must be 'natural light' or follow pattern 'XXL:XXD' (e.g., '12L:12D'), got '{v}'"
            )
        return v

    @field_validator(
        'time_post_fertilisation',
        'pre_hatching_water_temperature_average',
        'post_hatching_water_temperature_average',
        'degree_days',
        'medium_replacement_frequency',
        'percentage_total_somite_number',
        'average_water_salinity',
        'generations_from_wild',
        mode='before'
    )
    def validate_numeric_fields(cls, v):
        if v == "restricted access" or v == "" or v is None:
            return v

        try:
            numeric_val = float(v)
            if numeric_val < 0:
                raise ValueError("Numeric value must be non-negative")
            return numeric_val
        except ValueError as e:
            if "non-negative" in str(e):
                raise
            raise ValueError(f"Value must be a valid number or 'restricted access', got '{v}'")

    @field_validator('percentage_total_somite_number')
    def validate_percentage_range(cls, v):
        if v == "restricted access" or v is None:
            return v

        if not (0 <= v <= 100):
            raise ValueError("Percentage must be between 0 and 100")
        return v

    # Convert empty strings to None for optional fields
    @field_validator(
        'generations_from_wild', 'generations_from_wild_unit',
        mode='before'
    )
    def convert_empty_strings_to_none(cls, v):
        if v is not None and v == "":
            return None
        return v

    class Config:
        populate_by_name = True
        validate_default = True
        validate_assignment = True
        extra = "forbid"