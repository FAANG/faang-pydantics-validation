from pydantic import BaseModel, Field, field_validator, HttpUrl
from generic_validator_classes import OntologyValidator
from typing import List, Optional, Union, Literal
import re
from datetime import datetime

from .standard_ruleset import SampleCoreMetadata


class SpecimenCollectionDate(BaseModel):
    value: Union[str, Literal["restricted access"]]
    units: Literal["YYYY-MM-DD", "YYYY-MM", "YYYY", "restricted access"]
    mandatory: Literal["mandatory"] = "mandatory"

    @field_validator('value')
    def validate_date_format(cls, v, info):
        if v == "restricted access":
            return v

        values = info.data
        unit = values.get('units')

        if unit == "YYYY-MM-DD":
            pattern = r'^[12]\d{3}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$'
        elif unit == "YYYY-MM":
            pattern = r'^[12]\d{3}-(0[1-9]|1[0-2])$'
        elif unit == "YYYY":
            pattern = r'^[12]\d{3}$'
        else:
            return v

        if not re.match(pattern, v):
            raise ValueError(f"Invalid date format: {v}. Must match {unit} pattern")

        return v


class GeographicLocation(BaseModel):
    value: Literal[
        "Afghanistan", "Albania", "Algeria", "American Samoa", "Andorra", "Angola", "Anguilla",
        "Antarctica", "Antigua and Barbuda", "Arctic Ocean", "Argentina", "Armenia", "Aruba",
        "Ashmore and Cartier Islands", "Atlantic Ocean", "Australia", "Austria", "Azerbaijan", "Bahamas",
        "Bahrain", "Baltic Sea", "Baker Island", "Bangladesh", "Barbados", "Bassas da India", "Belarus",
        "Belgium", "Belize", "Benin", "Bermuda", "Bhutan", "Bolivia", "Borneo", "Bosnia and Herzegovina",
        "Botswana", "Bouvet Island", "Brazil", "British Virgin Islands", "Brunei", "Bulgaria", "Burkina Faso",
        "Burundi", "Cambodia", "Cameroon", "Canada", "Cape Verde", "Cayman Islands", "Central African Republic",
        "Chad", "Chile", "China", "Christmas Island", "Clipperton Island", "Cocos Islands", "Colombia", "Comoros",
        "Cook Islands", "Coral Sea Islands", "Costa Rica", "Cote d'Ivoire", "Croatia", "Cuba", "Curacao",
        "Cyprus", "Czech Republic", "Democratic Republic of the Congo", "Denmark", "Djibouti", "Dominica",
        "Dominican Republic", "Ecuador", "Egypt", "El Salvador", "Equatorial Guinea", "Eritrea", "Estonia",
        "Eswatini", "Ethiopia", "Europa Island", "Falkland Islands (Islas Malvinas)", "Faroe Islands", "Fiji",
        "Finland", "France", "French Guiana", "French Polynesia", "French Southern and Antarctic Lands", "Gabon",
        "Gambia", "Gaza Strip", "Georgia", "Germany", "Ghana", "Gibraltar", "Glorioso Islands", "Greece",
        "Greenland", "Grenada", "Guadeloupe", "Guam", "Guatemala", "Guernsey", "Guinea", "Guinea-Bissau",
        "Guyana", "Haiti", "Heard Island and McDonald Islands", "Honduras", "Hong Kong", "Howland Island",
        "Hungary", "Iceland", "India", "Indian Ocean", "Indonesia", "Iran", "Iraq", "Ireland", "Isle of Man",
        "Israel", "Italy", "Jamaica", "Jan Mayen", "Japan", "Jarvis Island", "Jersey", "Johnston Atoll", "Jordan",
        "Juan de Nova Island", "Kazakhstan", "Kenya", "Kerguelen Archipelago", "Kingman Reef", "Kiribati",
        "Kosovo", "Kuwait", "Kyrgyzstan", "Laos", "Latvia", "Lebanon", "Lesotho", "Liberia", "Libya",
        "Liechtenstein", "Line Islands", "Lithuania", "Luxembourg", "Macau", "Madagascar", "Malawi", "Malaysia",
        "Maldives", "Mali", "Malta", "Marshall Islands", "Martinique", "Mauritania", "Mauritius", "Mayotte",
        "Mediterranean Sea", "Mexico", "Micronesia, Federated States of", "Midway Islands", "Moldova", "Monaco",
        "Mongolia", "Montenegro", "Montserrat", "Morocco", "Mozambique", "Myanmar", "Namibia", "Nauru",
        "Navassa Island", "Nepal", "Netherlands", "New Caledonia", "New Zealand", "Nicaragua", "Niger", "Nigeria",
        "Niue", "Norfolk Island", "North Korea", "North Macedonia", "North Sea", "Northern Mariana Islands",
        "Norway", "Oman", "Pacific Ocean", "Pakistan", "Palau", "Palmyra Atoll", "Panama", "Papua New Guinea",
        "Paracel Islands", "Paraguay", "Peru", "Philippines", "Pitcairn Islands", "Poland", "Portugal",
        "Puerto Rico", "Qatar", "Republic of the Congo", "Reunion", "Romania", "Ross Sea", "Russia", "Rwanda",
        "Saint Barthelemy", "Saint Helena", "Saint Kitts and Nevis", "Saint Lucia", "Saint Martin",
        "Saint Pierre and Miquelon", "Saint Vincent and the Grenadines", "Samoa", "San Marino",
        "Sao Tome and Principe", "Saudi Arabia", "Senegal", "Serbia", "Seychelles", "Sierra Leone", "Singapore",
        "Sint Maarten", "Slovakia", "Slovenia", "Solomon Islands", "Somalia", "South Africa",
        "South Georgia and the South Sandwich Islands", "South Korea", "South Sudan", "Southern Ocean", "Spain",
        "Spratly Islands", "Sri Lanka", "State of Palestine", "Sudan", "Suriname", "Svalbard", "Sweden",
        "Switzerland", "Syria", "Taiwan", "Tajikistan", "Tanzania", "Tasman Sea", "Thailand", "Timor-Leste",
        "Togo", "Tokelau", "Tonga", "Trinidad and Tobago", "Tromelin Island", "Tunisia", "Turkey", "Turkmenistan",
        "Turks and Caicos Islands", "Tuvalu", "USA", "Uganda", "Ukraine", "United Arab Emirates",
        "United Kingdom", "Uruguay", "Uzbekistan", "Vanuatu", "Venezuela", "Viet Nam", "Virgin Islands",
        "Wake Island", "Wallis and Futuna", "West Bank", "Western Sahara", "Yemen", "Zambia", "Zimbabwe",
        "Belgian Congo", "British Guiana", "Burma", "Czechoslovakia", "East Timor",
        "Former Yugoslav Republic of Macedonia", "Korea", "Macedonia", "Micronesia", "Netherlands Antilles",
        "Serbia and Montenegro", "Siam", "Swaziland", "The former Yugoslav Republic of Macedonia", "USSR",
        "Yugoslavia", "Zaire", "restricted access"
    ]
    mandatory: Literal["mandatory"] = "mandatory"


class AnimalAgeAtCollection(BaseModel):
    value: Union[float, Literal["restricted access"]]
    units: Literal[
        "minutes", "hours", "month", "year", "days", "weeks", "months", "years",
        "minute", "hour", "day", "week", "restricted access"
    ]
    mandatory: Literal["mandatory"] = "mandatory"

    @field_validator('value')
    def validate_age_value(cls, v):
        if v == "restricted access":
            return v

        if isinstance(v, (int, float)) and v < 0:
            raise ValueError("Age must be non-negative")

        return v


class DevelopmentalStage(BaseModel):
    text: str
    term: Union[str, Literal["restricted access"]]
    mandatory: Literal["mandatory"] = "mandatory"
    ontology_name: Optional[Literal["EFO", "UBERON"]] = None

    @field_validator('term')
    def validate_developmental_stage_term(cls, v, info):
        if v == "restricted access":
            return v

        # Convert underscore to colon if needed
        term_with_colon = v.replace('_', ':', 1) if '_' in v else v

        # Determine ontology based on term prefix or ontology_name
        values = info.data
        ontology_name = values.get('ontology_name')

        if term_with_colon.startswith("EFO:"):
            ontology_name = "EFO"
        elif term_with_colon.startswith("UBERON:"):
            ontology_name = "UBERON"
        elif not ontology_name:
            # Default to EFO if no clear indication
            ontology_name = "EFO"

        # Ontology validation
        ov = OntologyValidator(cache_enabled=True)
        res = ov.validate_ontology_term(
            term=term_with_colon,
            ontology_name=ontology_name,
            allowed_classes=["EFO:0000399", "UBERON:0000105"]
        )
        if res.errors:
            raise ValueError(f"Developmental stage term invalid: {res.errors}")

        return v


class HealthStatusAtCollection(BaseModel):
    text: str
    term: Union[str, Literal["not applicable", "not collected", "not provided", "restricted access"]]
    mandatory: Literal["recommended"] = "recommended"
    ontology_name: Optional[Literal["PATO", "EFO"]] = None

    @field_validator('term')
    def validate_health_status_term(cls, v, info):
        if v in ["not applicable", "not collected", "not provided", "restricted access"]:
            return v

        # Convert underscore to colon if needed
        term_with_colon = v.replace('_', ':', 1) if '_' in v else v

        # Determine ontology based on term prefix
        values = info.data
        ontology_name = values.get('ontology_name', "PATO")

        if term_with_colon.startswith("PATO:"):
            ontology_name = "PATO"
        elif term_with_colon.startswith("EFO:"):
            ontology_name = "EFO"

        # Ontology validation
        ov = OntologyValidator(cache_enabled=True)
        res = ov.validate_ontology_term(
            term=term_with_colon,
            ontology_name=ontology_name,
            allowed_classes=["PATO:0000461", "EFO:0000408"]
        )
        if res.errors:
            raise ValueError(f"Health status term invalid: {res.errors}")

        return v


class OrganismPart(BaseModel):
    text: str
    term: Union[str, Literal["restricted access"]]
    mandatory: Literal["mandatory"] = "mandatory"
    ontology_name: Optional[Literal["UBERON", "BTO"]] = None

    @field_validator('term')
    def validate_organism_part_term(cls, v, info):
        if v == "restricted access":
            return v

        # Convert underscore to colon if needed
        term_with_colon = v.replace('_', ':', 1) if '_' in v else v

        # Determine ontology based on term prefix
        values = info.data
        ontology_name = values.get('ontology_name')

        if term_with_colon.startswith("UBERON:"):
            ontology_name = "UBERON"
        elif term_with_colon.startswith("BTO:"):
            ontology_name = "BTO"
        elif not ontology_name:
            # Default to UBERON if no clear indication
            ontology_name = "UBERON"

        # Ontology validation
        ov = OntologyValidator(cache_enabled=True)
        res = ov.validate_ontology_term(
            term=term_with_colon,
            ontology_name=ontology_name,
            allowed_classes=["UBERON:0001062", "BTO:0000042"]
        )
        if res.errors:
            raise ValueError(f"Organism part term invalid: {res.errors}")

        return v


class SpecimenCollectionProtocol(BaseModel):
    value: Union[str, Literal["restricted access"]]
    mandatory: Literal["mandatory"] = "mandatory"

    @field_validator('value')
    def validate_protocol_url(cls, v):
        if v == "restricted access":
            return v

        # Validate URL format
        if not (v.startswith('http://') or v.startswith('https://') or v.startswith('ftp://')):
            raise ValueError("Protocol must be a valid URL starting with http://, https://, or ftp://")

        return v


class FastedStatus(BaseModel):
    value: Literal["fed", "fasted", "unknown"]
    mandatory: Literal["optional"] = "optional"


class NumberOfPieces(BaseModel):
    value: float
    units: Literal["count"] = "count"
    mandatory: Literal["optional"] = "optional"

    @field_validator('value')
    def validate_count(cls, v):
        if v < 0:
            raise ValueError("Number of pieces must be non-negative")
        return v


class SpecimenVolume(BaseModel):
    value: float
    units: Literal["square centimeters", "liters", "milliliters"]
    mandatory: Literal["optional"] = "optional"

    @field_validator('value')
    def validate_volume(cls, v):
        if v < 0:
            raise ValueError("Volume must be non-negative")
        return v


class SpecimenSize(BaseModel):
    value: float
    units: Literal[
        "meters", "centimeters", "millimeters",
        "square meters", "square centimeters", "square millimeters"
    ]
    mandatory: Literal["optional"] = "optional"

    @field_validator('value')
    def validate_size(cls, v):
        if v < 0:
            raise ValueError("Size must be non-negative")
        return v


class SpecimenWeight(BaseModel):
    value: float
    units: Literal["grams", "kilograms"]
    mandatory: Literal["optional"] = "optional"

    @field_validator('value')
    def validate_weight(cls, v):
        if v < 0:
            raise ValueError("Weight must be non-negative")
        return v


class SpecimenPictureUrl(BaseModel):
    value: str
    mandatory: Literal["optional"] = "optional"

    @field_validator('value')
    def validate_picture_url(cls, v):
        if not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError("Picture URL must be a valid URL starting with http:// or https://")
        return v


class GestationalAgeAtSampleCollection(BaseModel):
    value: float
    units: Literal["days", "weeks", "day", "week"]
    mandatory: Literal["optional"] = "optional"

    @field_validator('value')
    def validate_gestational_age(cls, v):
        if v < 0:
            raise ValueError("Gestational age must be non-negative")
        return v


class AverageIncubationTemperature(BaseModel):
    value: float
    units: Literal["degrees celsius"] = "degrees celsius"
    mandatory: Literal["optional"] = "optional"


class AverageIncubationHumidity(BaseModel):
    value: float
    units: Literal["%"] = "%"
    mandatory: Literal["optional"] = "optional"

    @field_validator('value')
    def validate_humidity(cls, v):
        if not (0 <= v <= 100):
            raise ValueError("Humidity must be between 0 and 100 percent")
        return v


class EmbryonicStage(BaseModel):
    value: Literal[
        "Early cleavage", "During cleavage", "Late cleavage",
        "1", "2", "3", "4", "5", "6", "7", "7 to 8-", "8", "9",
        "9+ to 10-", "10", "11", "12", "13", "13+ to 14-", "14",
        "14+ to 15-", "15", "16", "17", "18", "19", "20", "21", "22", "23",
        "24", "25", "26", "27", "28", "29", "30", "31", "32", "33", "34",
        "35", "36", "37", "38", "39", "40", "41", "42", "43", "44", "45", "46"
    ]
    units: Literal["stage Hamburger Hamilton"] = "stage Hamburger Hamilton"
    mandatory: Literal["optional"] = "optional"


class DerivedFrom(BaseModel):
    value: str
    mandatory: Literal["mandatory"] = "mandatory"

    @field_validator('value')
    def validate_derived_from(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Derived from value is required and cannot be empty")
        return v.strip()


class FAANGSpecimenFromOrganismSample(SampleCoreMetadata):
    # Required nested fields from JSON schema
    specimen_collection_date: SpecimenCollectionDate
    geographic_location: GeographicLocation
    animal_age_at_collection: AnimalAgeAtCollection
    developmental_stage: DevelopmentalStage
    organism_part: OrganismPart
    specimen_collection_protocol: SpecimenCollectionProtocol
    derived_from: DerivedFrom

    # Recommended fields (items within are recommended)
    health_status_at_collection: Optional[List[HealthStatusAtCollection]] = Field(
        None, json_schema_extra={"recommended": True}
    )

    # Optional fields
    fasted_status: Optional[FastedStatus] = None
    number_of_pieces: Optional[NumberOfPieces] = None
    specimen_volume: Optional[SpecimenVolume] = None
    specimen_size: Optional[SpecimenSize] = None
    specimen_weight: Optional[SpecimenWeight] = None
    specimen_picture_url: Optional[List[SpecimenPictureUrl]] = None
    gestational_age_at_sample_collection: Optional[GestationalAgeAtSampleCollection] = None
    average_incubation_temperature: Optional[AverageIncubationTemperature] = None
    average_incubation_humidity: Optional[AverageIncubationHumidity] = None
    embryonic_stage: Optional[EmbryonicStage] = None

    # Custom field to extract sample name from samples_core
    sample_name: Optional[str] = Field(None, exclude=True)

    def __init__(self, **data):
        # Extract sample name from samples_core if present
        if 'samples_core' in data and 'sample_description' in data['samples_core']:
            sample_desc = data['samples_core']['sample_description']
            if isinstance(sample_desc, dict) and 'value' in sample_desc:
                data['sample_name'] = sample_desc['value']

        # Extract custom sample_name if present (priority over samples_core)
        if 'custom' in data and 'sample_name' in data['custom']:
            sample_name_data = data['custom']['sample_name']
            if isinstance(sample_name_data, dict) and 'value' in sample_name_data:
                data['sample_name'] = sample_name_data['value']

        # Ensure we have a sample name from somewhere
        if 'sample_name' not in data or not data['sample_name']:
            raise ValueError("Sample name is required but could not be extracted from data structure")

        super().__init__(**data)

    @field_validator('sample_name')
    def validate_sample_name(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Sample Name is required and cannot be empty")
        return v.strip()

    class Config:
        populate_by_name = True
        validate_default = True
        validate_assignment = True
        extra = "forbid"