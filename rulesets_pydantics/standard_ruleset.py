from pydantic import BaseModel, Field, field_validator, HttpUrl
from typing import Optional, List, Literal


class SampleCoreMetadata(BaseModel):
    # Required fields
    sample_name: str = Field(..., alias="Sample Name")
    sample_description: Optional[str] = Field(None, alias="Sample Description")
    material: str = Field(..., alias="Material")
    term_source_id: str = Field(..., alias="Term Source ID")
    project: Literal["FAANG"] = Field(..., alias="Project")

    # Optional fields
    secondary_project: Optional[str] = Field(None, alias="Secondary Project")
    availability: Optional[str] = Field(None, alias="Availability")
    same_as: Optional[str] = Field(None, alias="Same as")

    @field_validator('term_source_id')
    def validate_material_term(cls, v, info):
        """Validate that the term matches the material type"""
        values = info.data
        material = values.get('Material') or values.get('material')  # Handle both cases

        material_term_mapping = {
            "organism": "OBI_0100026",
            "specimen from organism": "OBI_0001479",
            "cell specimen": "OBI_0001468",
            "single cell specimen": "OBI_0002127",
            "pool of specimens": "OBI_0302716",
            "cell culture": "OBI_0001876",
            "cell line": "CLO_0000031",
            "organoid": "NCIT_C172259",
            "restricted access": "restricted access",
        }

        expected_term = material_term_mapping.get(material)
        if expected_term and v != expected_term:
            raise ValueError(f"Term '{v}' does not match material '{material}'. Expected: '{expected_term}'")

        return v

    @field_validator('availability')
    def validate_availability_format(cls, v):
        """Validate availability URL/email format if provided"""
        if not v or v.strip() == "":  # Allow empty strings
            return v

        if not (v.startswith('http://') or v.startswith('https://') or v.startswith('mailto:')):
            raise ValueError("Availability must be a web URL or email address with 'mailto:' prefix")
        return v

    class Config:
        populate_by_name = True  # Updated for Pydantic v2
        validate_default = True
        validate_assignment = True