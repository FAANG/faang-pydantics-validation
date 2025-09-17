from pydantic import ValidationError
from typing import List, Optional, Dict, Any, Tuple
import json
from organism_validator_classes import OntologyValidator, BreedSpeciesValidator, RelationshipValidator

from rulesets_pydantics.organism_ruleset import FAANGOrganismSample


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
        validate_with_json_schema: bool = True
    ) -> Tuple[Optional[FAANGOrganismSample], Dict[str, List[str]]]:

        errors_dict = {
            'errors': [],
            'warnings': [],
            'field_errors': {}
        }

        # pydantic validation
        try:
            organism_model = FAANGOrganismSample(**data)
        except ValidationError as e:
            for error in e.errors():
                field_path = '.'.join(str(x) for x in error['loc'])
                error_msg = error['msg']

                if field_path not in errors_dict['field_errors']:
                    errors_dict['field_errors'][field_path] = []
                errors_dict['field_errors'][field_path].append(error_msg)
                errors_dict['errors'].append(f"{field_path}: {error_msg}")

            return None, errors_dict
        except Exception as e:
            errors_dict['errors'].append(str(e))
            return None, errors_dict

        # recommended fields
        recommended_fields = ['birth_date', 'breed', 'health_status']
        for field in recommended_fields:
            if getattr(organism_model, field, None) is None:
                errors_dict['warnings'].append(
                    f"Field '{field}' is recommended but was not provided"
                )

        return organism_model, errors_dict


    def validate_with_pydantic(
        self,
        organisms: List[Dict[str, Any]],
        validate_relationships: bool = True,
    ) -> Dict[str, Any]:

        results = {
            'valid_organisms': [],
            'invalid_organisms': [],
            'summary': {
                'total': len(organisms),
                'valid': 0,
                'invalid': 0,
                'warnings': 0,
                'relationship_errors': 0
            }
        }

        # validate organisms
        for i, org_data in enumerate(organisms):
            sample_name = org_data.get('Sample Name', f'organism_{i}')

            model, errors = self.validate_organism_sample(
                org_data,
                validate_relationships=False
            )

            if model and not errors['errors']:
                results['valid_organisms'].append({
                    'index': i,
                    'sample_name': sample_name,
                    'model': model,
                    'data': org_data,
                    'warnings': errors['warnings'],
                    'relationship_errors': []
                })
                results['summary']['valid'] += 1
                if errors['warnings']:
                    results['summary']['warnings'] += 1
            else:
                results['invalid_organisms'].append({
                    'index': i,
                    'sample_name': sample_name,
                    'data': org_data,
                    'errors': errors
                })
                results['summary']['invalid'] += 1

        # Validate relationships between organisms
        if validate_relationships and results['valid_organisms']:
            valid_organism_data = [org['data'] for org in results['valid_organisms']]
            relationship_errors = self.relationship_validator.validate_relationships(
                valid_organism_data
            )

            # relationship errors
            for org in results['valid_organisms']:
                sample_name = org['sample_name']
                if sample_name in relationship_errors:
                    org['relationship_errors'] = relationship_errors[sample_name]
                    results['summary']['relationship_errors'] += 1

        return results

# Validate parent-child relationships between organisms
    def validate_relationships(
        self,
        models: List[FAANGOrganismSample],
        raw_data: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        errors_by_sample = {}

        # Create sample map
        sample_map = {}
        for i, (model, data) in enumerate(zip(models, raw_data)):
            sample_name = data.get('Sample Name', f'organism_{i}')
            sample_map[sample_name] = model

        # Validate relationships
        for sample_name, model in sample_map.items():
            if not model.child_of:
                continue

            sample_errors = []

            # check maximum parents
            if len(model.child_of) > 2:
                sample_errors.append(f"Organism can have at most 2 parents, found {len(model.child_of)}")

            # Check each parent
            for parent_id in model.child_of:
                if parent_id == "restricted access":
                    continue

                if parent_id in sample_map:
                    parent_model = sample_map[parent_id]

                    # check species match
                    if model.organism != parent_model.organism:
                        sample_errors.append(
                            f"Species mismatch: child is '{model.organism}' "
                            f"but parent '{parent_id}' is '{parent_model.organism}'"
                        )

                    # circular relationships
                    if parent_model.child_of:
                        for grandparent_id in parent_model.child_of:
                            if grandparent_id == sample_name:
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


def export_organism_to_biosample_format(model: FAANGOrganismSample) -> Dict[str, Any]:

    def convert_term_to_url(term_id: str) -> str:
        if not term_id or term_id in ["restricted access", ""]:
            return ""
        if '_' in term_id and ':' not in term_id:
            term_colon = term_id.replace('_', ':', 1)
        else:
            term_colon = term_id
        return f"http://purl.obolibrary.org/obo/{term_colon.replace(':', '_')}"


    biosample_data = {
        "characteristics": {}
    }

    # material
    biosample_data["characteristics"]["material"] = [{
        "text": model.material,
        "ontologyTerms": [convert_term_to_url(model.term_source_id)]
    }]

    # organism
    biosample_data["characteristics"]["organism"] = [{
        "text": model.organism,
        "ontologyTerms": [convert_term_to_url(model.organism_term_source_id)]
    }]

    # sex
    biosample_data["characteristics"]["sex"] = [{
        "text": model.sex,
        "ontologyTerms": [convert_term_to_url(model.sex_term_source_id)]
    }]

    # birth date
    if model.birth_date and model.birth_date.strip():
        biosample_data["characteristics"]["birth date"] = [{
            "text": model.birth_date,
            "unit": model.birth_date_unit or ""
        }]

    # breed
    if model.breed and model.breed.strip():
        biosample_data["characteristics"]["breed"] = [{
            "text": model.breed,
            "ontologyTerms": [convert_term_to_url(model.breed_term_source_id)]
        }]

    # Health status (keep existing format)
    if model.health_status:
        biosample_data["characteristics"]["health status"] = []
        for status in model.health_status:
            biosample_data["characteristics"]["health status"].append({
                "text": status.text,
                "ontologyTerms": [f"http://purl.obolibrary.org/obo/{status.term.replace(':', '_')}"]
            })

    # relationships
    if model.child_of:
        biosample_data["relationships"] = []
        for parent in model.child_of:
            if parent and parent.strip():
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

    # validation errors
    if validation_results['invalid_organisms']:
        report.append("\n\nValidation Errors:")
        report.append("-" * 20)
        for org in validation_results['invalid_organisms']:
            report.append(f"\nOrganism: {org['sample_name']} (index: {org['index']})")
            for field, field_errors in org['errors'].get('field_errors', {}).items():
                for error in field_errors:
                    report.append(f"  ERROR in {field}: {error}")
            for error in org['errors'].get('errors', []):
                if not any(error.startswith(field) for field in org['errors'].get('field_errors', {})):
                    report.append(f"  ERROR: {error}")

    # warnings and relationship issues
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


if __name__ == "__main__":
    # Test with the new JSON format
    json_string = """
     {
         "organism": [
             {
                 "Sample Name": "ECA_UKY_H11",
                 "Sample Description": "Foal",
                 "Material": "organism",
                 "Term Source ID": "OBI_0100026",
                 "Project": "FAANG",
                 "Secondary Project": "AQUA-FAANG",
                 "Availability": "",
                 "Same as": "",
                 "Organism": "Equus caballus",
                 "Organism Term Source ID": "NCBITaxon:333920",
                 "Sex": "male",
                 "Sex Term Source ID": "PATO_0000384",
                 "Birth Date": "2013-02",
                 "Unit": "YYYY-MM",
                 "Health Status": [
                     {
                         "text": "normal",
                         "term": "PATO:0000461"
                     }
                 ],
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
                 "Child Of": ["", ""],
                 "Pedigree": ""
             },
            {
                 "Sample Name": "ECA_UKY_H1",
                 "Sample Description": "Foal, 9 days old, Thoroughbred",
                 "Material": "organism",
                 "Term Source ID": "OBI_0100026",
                 "Project": "FAANG",
                 "Secondary Project": "AQUA-FAANG",
                 "Availability": "",
                 "Same as": "",
                 "Organism": "Equus caballus",
                 "Organism Term Source ID": "NCBITaxon:3037151",
                 "Sex": "female",
                 "Sex Term Source ID": "PATO_0000383",
                 "Birth Date": "014-07",
                 "Unit": "YYYY-MM",
                 "Health Status": [
                     {
                         "text": "normal",
                         "term": "PATO:0000461"
                     }
                 ],
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
                 "Child Of": ["aaa", ""],
                 "Pedigree": ""
             }
         ]
     }
     """

    data = json.loads(json_string)
    sample_organisms = data.get("organism", [])

    validator = PydanticValidator()
    results = validator.validate_with_pydantic(sample_organisms)

    report = generate_validation_report(results)
    print(report)

    # Export to BioSamples format if valid
    if results['valid_organisms']:
        for valid_org in results['valid_organisms']:
            biosample_data = export_organism_to_biosample_format(valid_org['model'])
            print(f"\nBioSample format for {valid_org['sample_name']}:")
            print(json.dumps(biosample_data, indent=2))