# FAANG Pydantics Validation System



A Pydantic-based validation system for FAANG. This system ensures data quality and compliance with FAANG metadata standards before submission to ENA or BioSamples.

## Overview

This validation framework provides:
- **Schema validation** using Pydantic models
- **Ontology term validation** against OLS (Ontology Lookup Service)
- **Relationship validation** between organism samples
- **Breed-species compatibility checks**

# Organism Sample Validation

## Features

### Core Validation Components

- **Field Validation**: Ensures all mandatory fields are present
- **Ontology Integration**: Validates terms against NCBITaxon, PATO, LBO, and EFO ontologies
- **Relationship Checking**: Validates parent-child relationships and prevents circular dependencies
- **Species-Breed Matching**: Ensures breed terms are appropriate for the specified species

### Supported Field Types

#### Required Fields
- **Organism**: NCBITaxon terms for species identification
- **Material**: OBI terms for material type (organism, specimen, cell culture, etc.)
- **Sex**: PATO terms for biological sex
- **Project**: Must be "FAANG"

#### Recommended Fields
- **Birth Date**: Supports YYYY-MM-DD, YYYY-MM, or YYYY formats
- **Breed**: LBO (Livestock Breed Ontology) terms
- **Health Status**: PATO or EFO terms for health conditions

#### Optional Fields
- Diet, birth location, birth weight, pregnancy details
- Parent-child relationships (child_of)
- Custom metadata fields

## Installation

```bash
# Install required dependencies
pip install -r requirements.txt
```

## Usage

### Basic Validation

```python
from organism_validation import PydanticValidator
import json

# Initialize validator
validator = PydanticValidator()

# Load your organism data
with open('organism_data.json', 'r') as f:
    data = json.load(f)

# Validate organisms
results = validator.validate_with_pydantic(data['organism'])

# Generate validation report
from organism_validation import generate_validation_report
report = generate_validation_report(results)
print(report)
```


## Data Format

### Input JSON Structure

```json
{
  "organism": [
    {
      "sample_description": {
        "value": "Adult female, 23.5 months of age, Thoroughbred"
      },
      "material": {
        "text": "organism",
        "term": "OBI:0100026"
      },
      "project": {
        "value": "FAANG"
      },
      "organism": {
        "text": "Equus caballus",
        "term": "NCBITaxon:9796"
      },
      "sex": {
        "text": "female",
        "term": "PATO:0000383"
      },
      "birth_date": {
        "value": "2020-05",
        "units": "YYYY-MM"
      },
      "breed": {
        "text": "Thoroughbred",
        "term": "LBO:0000001"
      },
      "health_status": [
        {
          "text": "normal",
          "term": "PATO:0000461"
        }
      ],
      "child_of": [
        {
          "value": "PARENT_SAMPLE_ID"
        }
      ],
      "custom": {
        "sample_name": {
          "value": "HORSE_001"
        }
      }
    }
  ]
}
```

## Validation Rules

### Ontology Requirements

| Field | Ontology | Example Term | Required |
|-------|----------|--------------|-------|
| Organism | NCBITaxon | NCBITaxon:9796 |  Yes |
| Sex | PATO | PATO:0000383 |  Yes |
| Material | OBI | OBI:0100026 |  Yes |
| Breed | LBO | LBO:0000001 |  Recommended |
| Health Status | PATO/EFO | PATO:0000461 |  Recommended |

### Special Values

Several fields accept special values for restricted or unavailable data:
- `"restricted access"` - Data is restricted
- `"not applicable"` - Field doesn't apply to this sample
- `"not collected"` - Data wasn't collected
- `"not provided"` - Data exists but wasn't provided

### Relationship Rules

- Maximum 2 parents per organism (child_of field)
- Parent and child must be the same species
- No circular relationships allowed
- Referenced parents must exist in the current batch or in BioSamples database




## Error Types

### Field Errors
- **Missing required fields**: `organism`, `sex`, `material`, `project`
- **Invalid formats**: Birth date format, URL format for availability
- **Type mismatches**: Incorrect data types for numeric fields

### Ontology Errors
- **Invalid terms**: Terms not found in specified ontology
- **Wrong ontology**: Using terms from incorrect ontology
- **Text-term mismatch**: Text doesn't match ontology term label

### Relationship Errors
- **Missing parents**: Referenced parent samples not found
- **Species mismatch**: Parent and child have different species
- **Circular relationships**: Parent lists child as its parent
- **Too many parents**: More than 2 parents specified
