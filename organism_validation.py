from pydantic import ValidationError
from typing import List, Optional, Dict, Any, Tuple
import json
from organism_validator_classes import OntologyValidator, BreedSpeciesValidator, RelationshipValidator

from rulesets_pydantics.organism_ruleset import (
    FAANGOrganismSample
)

class PydanticValidator:
    def __init__(self, schema_file_path: str = None):
        self.relationship_validator = RelationshipValidator()
        self.ontology_validator = OntologyValidator(cache_enabled=True)
        self.breed_validator = BreedSpeciesValidator(self.ontology_validator)
        self.schema_file_path = schema_file_path or "faang_samples_organism.metadata_rules.json"
        self._schema = None


    def validate_organism_sample(
        self,
        data: Dict[str, Any],
        validate_relationships: bool = True,
        validate_ontologies: bool = True,
        validate_with_json_schema: bool = True
    ) -> Tuple[Optional[Dict[str, Any]], Dict[str, List[str]]]:

        errors_dict = {
            'errors': [],
            'warnings': [],
            'field_errors': {}
        }

        # Basic validation for required fields
        required_fields = [
            "Sample Name", "Material", "Term Source ID", "Project",
            "Organism", "Organism Term Source ID", "Sex", "Sex Term Source ID"
        ]

        for field in required_fields:
            if field not in data:
                if field not in errors_dict['field_errors']:
                    errors_dict['field_errors'][field] = []
                errors_dict['field_errors'][field].append(f"Field '{field}' is required")
                errors_dict['errors'].append(f"{field}: Field is required")

        if errors_dict['errors']:
            return None, errors_dict

        # Validate material
        if data["Material"] != "organism":
            field = "Material"
            if field not in errors_dict['field_errors']:
                errors_dict['field_errors'][field] = []
            errors_dict['field_errors'][field].append(f"Material must be 'organism', got '{data['Material']}'")
            errors_dict['errors'].append(f"{field}: Material must be 'organism', got '{data['Material']}'")

        # Validate project
        if data["Project"] != "FAANG":
            field = "Project"
            if field not in errors_dict['field_errors']:
                errors_dict['field_errors'][field] = []
            errors_dict['field_errors'][field].append(f"Project must be 'FAANG', got '{data['Project']}'")
            errors_dict['errors'].append(f"{field}: Project must be 'FAANG', got '{data['Project']}'")

        # Validate Health Status
        if "Health Status" in data:
            health_status = data["Health Status"].split(",")
            if not isinstance(health_status, list) and not isinstance(health_status, str):
                if "Health Status" not in errors_dict['field_errors']:
                    errors_dict['field_errors']["Health Status"] = []
                errors_dict['field_errors']["Health Status"].append("Health Status must be a list")
                errors_dict['errors'].append("Health Status: Health Status must be a list")
            else:
                # Validate each health status value
                for status in health_status:
                    if not isinstance(status, str):
                        if "Health Status" not in errors_dict['field_errors']:
                            errors_dict['field_errors']["Health Status"] = []
                        errors_dict['field_errors']["Health Status"].append(
                            f"Health Status values must be strings, got {type(status)}"
                        )
                        errors_dict['errors'].append(
                            f"Health Status: values must be strings, got {type(status)}"
                        )

        # Validate Secondary Project
        if "Secondary Project" in data:
            secondary_project = data["Secondary Project"].split(",")
            if not isinstance(secondary_project, list):
                if "Secondary Project" not in errors_dict['field_errors']:
                    errors_dict['field_errors']["Secondary Project"] = []
                errors_dict['field_errors']["Secondary Project"].append(
                    "Secondary Project must be a list"
                )
                errors_dict['errors'].append(
                    "Secondary Project: Secondary Project must be a list"
                )
            else:
                # Validate each secondary project value
                for project in secondary_project:
                    if not isinstance(project, str):
                        if "Secondary Project" not in errors_dict['field_errors']:
                            errors_dict['field_errors']["Secondary Project"] = []
                        errors_dict['field_errors']["Secondary Project"].append(
                            f"Secondary Project values must be strings, got {type(project)}"
                        )
                        errors_dict['errors'].append(
                            f"Secondary Project: values must be strings, got {type(project)}"
                        )

        # recommended fields
        recommended_fields = ['Birth Date', 'Breed', 'Health Status']
        for field in recommended_fields:
            if field not in data or not data[field]:
                errors_dict['warnings'].append(
                    f"Field '{field}' is recommended but was not provided"
                )

        # ontology validation
        if validate_ontologies and not errors_dict['errors']:
            ontology_errors = self.validate_ontologies(data)
            errors_dict['errors'].extend(ontology_errors)

        if errors_dict['errors']:
            return None, errors_dict

        return data, errors_dict

    def validate_ontologies(self, data: Dict[str, Any]) -> List[str]:
        errors = []

        # Validate organism term
        organism_term = data.get("Organism Term Source ID")
        if organism_term != "restricted access":
            # Convert underscore to colon for validation
            organism_term_colon = organism_term.replace("_", ":")
            if not organism_term_colon.startswith("NCBITaxon:"):
                errors.append(f"Organism term '{organism_term}' should be from NCBITaxon ontology")

        # Validate sex term
        sex_term = data.get("Sex Term Source ID")
        if sex_term != "restricted access":
            # Convert underscore to colon for validation
            sex_term_colon = sex_term.replace("_", ":")
            if not sex_term_colon.startswith("PATO:"):
                errors.append(f"Sex term '{sex_term}' should be from PATO ontology")

        # Validate breed against species
        breed = data.get("Breed")
        breed_term = data.get("Breed Term Source ID")
        if breed and breed_term and organism_term:
            # Convert underscores to colons for validation
            breed_term_colon = breed_term.replace("_", ":")
            organism_term_colon = organism_term.replace("_", ":")

            # Skip validation for now to avoid errors
            #  We'll need to update the breed validator to handle the new format
            breed_errors = self.breed_validator.validate_breed_for_species(
                organism_term_colon,
                breed_term_colon
            )
            if breed_errors:
                errors.append(
                    f"Breed '{breed}' doesn't match the animal "
                    f"species: '{data.get('Organism')}'"
                )

        # Validate health status
        health_status = data.get("Health Status", [])
        health_status_term = data.get("Health Status Term Source ID")
        if health_status and health_status_term:
            if health_status_term not in ["not applicable", "not collected", "not provided", "restricted access"]:
                # Convert underscore to colon for validation
                health_status_term_colon = health_status_term.replace("_", ":")
                if not (health_status_term_colon.startswith("PATO:") or health_status_term_colon.startswith("EFO:")):
                    errors.append(
                        f"Health status term '{health_status_term}' should be from PATO or EFO ontology"
                    )

        return errors

    def validate_organism_relationships(
        self,
        data: Dict[str, Any],
        sample_name: str
    ) -> List[str]:
        errors = []

        child_of = data.get("Child Of", [])
        if not child_of:
            return errors

        # max 2 parents
        if len(child_of) > 2:
            errors.append(f"Organism can have at most 2 parents, found {len(child_of)}")

        # Additional relationship checks would go here
        # (checking parent existence, species match, etc.)

        return errors

    def validate_with_pydantic(
        self,
        organisms: List[Dict[str, Any]]
    ) -> Dict[str, Any]:

        results = {
            'valid_organisms': [],
            'invalid_organisms': [],
            'summary': {
                'total': len(organisms),
                'valid': 0,
                'invalid': 0,
                'warnings': 0
            }
        }

        # validate organisms
        for i, org_data in enumerate(organisms):
            sample_name = org_data.get('Sample Name')

            validated_data, errors = self.validate_organism_sample(
                org_data,
                validate_relationships=False
            )

            if validated_data and not errors['errors']:
                results['valid_organisms'].append({
                    'index': i,
                    'sample_name': sample_name,
                    'data': validated_data,
                    'warnings': errors['warnings']
                })
                results['summary']['valid'] += 1
                if errors['warnings']:
                    results['summary']['warnings'] += 1
            else:
                results['invalid_organisms'].append({
                    'index': i,
                    'sample_name': sample_name,
                    'errors': errors
                })
                results['summary']['invalid'] += 1

        # validate relationships
        if results['valid_organisms']:
            relationship_errors = self.validate_relationships(
                [org['data'] for org in results['valid_organisms']],
                organisms
            )

            # relationship errors
            for sample_name, errors in relationship_errors.items():
                for org in results['valid_organisms']:
                    if org['sample_name'] == sample_name:
                        if 'relationship_errors' not in org:
                            org['relationship_errors'] = []
                        org['relationship_errors'].extend(errors)
                        break

        return results

    def validate_relationships(
        self,
        data_list: List[Dict[str, Any]],
        raw_data: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        errors_by_sample = {}

        sample_map = {}
        for i, data in enumerate(data_list):
            sample_name = data.get('Sample Name', f'organism_{i}')
            sample_map[sample_name] = data

        # organism relationships
        for sample_name, data in sample_map.items():
            child_of = data.get('Child Of', [])
            if not child_of:
                continue

            sample_errors = []

            if len(child_of) > 2:
                sample_errors.append(f"Organism can have at most 2 parents, found {len(child_of)}")

            for parent_id in child_of:
                if parent_id == "restricted access":
                    continue

                if parent_id in sample_map:
                    parent_data = sample_map[parent_id]

                    # check species match
                    if data.get('Organism') != parent_data.get('Organism'):
                        sample_errors.append(
                            f"Species mismatch: child is '{data.get('Organism')}' "
                            f"but parent '{parent_id}' is '{parent_data.get('Organism')}'"
                        )

                    # circular relationships
                    parent_child_of = parent_data.get('Child Of', [])
                    if parent_child_of:
                        for grandparent in parent_child_of:
                            if grandparent == sample_name:
                                sample_errors.append(
                                    f"Circular relationship detected: '{parent_id}' "
                                    f"lists '{sample_name}' as its parent"
                                )
                else:
                    sample_errors.append(
                        f"Parent '{parent_id}' not found in current batch"
                    )

            if sample_errors:
                errors_by_sample[sample_name] = sample_errors

        return errors_by_sample

def export_organism_to_biosample_format(data: Dict[str, Any]) -> Dict[str, Any]:
    biosample_data = {
        "characteristics": {}
    }

    biosample_data["characteristics"]["material"] = [{
        "text": data.get("Material", ""),
        "ontologyTerms": [f"http://purl.obolibrary.org/obo/{data.get('Material Term Source ID', '').replace(':', '_')}"]
    }]

    biosample_data["characteristics"]["organism"] = [{
        "text": data.get("Organism", ""),
        "ontologyTerms": [f"http://purl.obolibrary.org/obo/{data.get('Organism Term Source ID', '').replace(':', '_')}"]
    }]

    biosample_data["characteristics"]["sex"] = [{
        "text": data.get("Sex", ""),
        "ontologyTerms": [f"http://purl.obolibrary.org/obo/{data.get('Sex Term Source ID', '').replace(':', '_')}"]
    }]

    if "Birth Date" in data and data["Birth Date"]:
        biosample_data["characteristics"]["birth date"] = [{
            "text": data["Birth Date"],
            "unit": data.get("Birth Date Unit", "")
        }]

    if "Breed" in data and data["Breed"]:
        biosample_data["characteristics"]["breed"] = [{
            "text": data["Breed"],
            "ontologyTerms": [f"http://purl.obolibrary.org/obo/{data.get('Breed Term Source ID', '').replace(':', '_')}"]
        }]

    if "Child Of" in data and data["Child Of"]:
        biosample_data["relationships"] = []
        for parent in data["Child Of"]:
            biosample_data["relationships"].append({
                "type": "child of",
                "target": parent
            })

    return biosample_data


def generate_validation_report(validation_results: Dict[str, Any]) -> str:
    report = []
    report.append("FAANG Organism Validation Report")
    report.append("=" * 40)
    report.append(f"\nTotal organisms processed: {validation_results['summary']['total']}")
    report.append(f"Valid organisms: {validation_results['summary']['valid']}")
    report.append(f"Invalid organisms: {validation_results['summary']['invalid']}")
    report.append(f"Organisms with warnings: {validation_results['summary']['warnings']}")

    if validation_results['invalid_organisms']:
        report.append("\n\nValidation Errors:")
        report.append("-" * 20)
        for org in validation_results['invalid_organisms']:
            report.append(f"\nOrganism: {org['sample_name']} (index: {org['index']})")
            # for error in org['errors']['errors']:
            #     report.append(f"  ERROR: {error}")
            for field, field_errors in org['errors']['field_errors'].items():
                for error in field_errors:
                    report.append(f"  ERROR in {field}: {error}")

    if validation_results['valid_organisms']:
        warnings_found = False
        for org in validation_results['valid_organisms']:
            if org.get('warnings') or org.get('relationship_errors'):
                if not warnings_found:
                    report.append("\n\nWarnings and Non-Critical Issues:")
                    report.append("-" * 30)
                    warnings_found = True

                report.append(f"\nOrganism: {org['sample_name']} (index: {org['index']})")
                for warning in org.get('warnings', []):
                    report.append(f"  WARNING: {warning}")
                for error in org.get('relationship_errors', []):
                    report.append(f"  RELATIONSHIP: {error}")

    return "\n".join(report)


def get_submission_status(validation_results: Dict[str, Any]) -> str:

    def has_issues(record: Dict[str, Any]) -> bool:
        for key, value in record.items():
            if key in ['samples_core', 'custom', 'experiments_core']:
                if has_issues(value):
                    return True
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and 'errors' in item and item['errors']:
                        return True
            elif isinstance(value, dict):
                if 'errors' in value and value['errors']:
                    return True
        return False

    for record_type, records in validation_results.items():
        for record in records:
            if has_issues(record):
                return 'Fix issues'

    return 'Ready for submission'


if __name__ == "__main__":

    json_string = """
    {
        "organism": [
          
       {
            "Sample Name": "ECA_UKY_H1",
            "Sample Description": "Adult female, 23.5 months of age, Thoroughbred",
            "Material": "organism",
            "Term Source ID": "OBI_0100026",
            "Project": "FAANG",
            "Secondary Project": "test",
            "Availability": "",
            "Same as": "",
            "Organism": "Equus caballus",
            "Organism Term Source ID": "NCBITaxon_9796",
            "Sex": "female",
            "Sex Term Source ID": "PATO_0000383",
            "Birth Date": "2009-04",
            "Unit": "YYYY-MM",
            "Breed": "Thoroughbred",
            "Breed Term Source ID": "LBO_0000910",
            "Health Status": "normal",
            "Health Status Term Source ID": "PATO_0000461",
            "Diet": "",
            "Birth Location": "",
            "Birth Location Latitude": "",
            "Birth Location Latitude Unit": "",
            "Birth Location Longitude": "",
            "Birth Location Longitude Unit": "",
            "Birth Weight": "",
            "Birth Weight Unit": "",
            "Placental Weight": "",
            "Placental Weight Unit": "",
            "Pregnancy Length": "",
            "Pregnancy Length Unit": "",
            "Delivery Timing": "",
            "Delivery Ease": "",
            "Child Of": [
                "",
                ""
            ],
            "Pedigree": ""
        }
        ]
    }
    """

    data = json.loads(json_string)
    sample_organisms = data["organism"]

    validator = PydanticValidator("rulesets-json/faang_samples_organism.metadata_rules.json")
    results = validator.validate_with_pydantic(sample_organisms)

    report = generate_validation_report(results)
    print(report)

    # export to BioSamples format
    if results['valid_organisms']:
        for valid_org in results['valid_organisms']:
            biosample_data = export_organism_to_biosample_format(valid_org['data'])
            # print(f"\nBioSample format for {valid_org['sample_name']}:")
            # print(json.dumps(biosample_data, indent=2))
