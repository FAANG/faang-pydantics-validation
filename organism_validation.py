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
        validate_ontologies: bool = True,
        validate_with_json_schema: bool = True
    ) -> Tuple[Optional[FAANGOrganismSample], Dict[str, List[str]]]:

        errors_dict = {
            'errors': [],
            'warnings': [],
            'field_errors': {}
        }

        # Pydantic validation
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

        # Additional ontology validation
        if validate_ontologies:
            ontology_errors = self.validate_ontologies(organism_model)
            errors_dict['errors'].extend(ontology_errors)

        return organism_model, errors_dict

    def validate_ontologies(self, model: FAANGOrganismSample) -> List[str]:
        """Validate ontology terms with actual ontology service"""
        errors = []

        # Convert underscore terms back to colon format for ontology validation
        def convert_term(term_id: str) -> str:
            if term_id and '_' in term_id and ':' not in term_id:
                return term_id.replace('_', ':', 1)
            return term_id

        # Validate organism term
        if model.organism_term_source_id and model.organism_term_source_id != "restricted access":
            term_colon = convert_term(model.organism_term_source_id)
            try:
                res = self.ontology_validator.validate_ontology_term(
                    term=term_colon,
                    ontology_name="NCBITaxon",
                    allowed_classes=["NCBITaxon"]
                )
                if res.errors:
                    errors.append(f"Organism term validation failed: {res.errors}")
            except Exception as e:
                errors.append(f"Error validating organism term: {str(e)}")

        # Validate sex term
        if model.sex_term_source_id and model.sex_term_source_id != "restricted access":
            term_colon = convert_term(model.sex_term_source_id)
            try:
                res = self.ontology_validator.validate_ontology_term(
                    term=term_colon,
                    ontology_name="PATO",
                    allowed_classes=["PATO:0000047"]
                )
                if res.errors:
                    errors.append(f"Sex term validation failed: {res.errors}")
            except Exception as e:
                errors.append(f"Error validating sex term: {str(e)}")

        # Validate breed term
        if (model.breed_term_source_id and
            model.breed_term_source_id not in ["not applicable", "restricted access", ""]):
            term_colon = convert_term(model.breed_term_source_id)
            try:
                res = self.ontology_validator.validate_ontology_term(
                    term=term_colon,
                    ontology_name="LBO",
                    allowed_classes=["LBO"]
                )
                if res.errors:
                    errors.append(f"Breed term validation failed: {res.errors}")
            except Exception as e:
                errors.append(f"Error validating breed term: {str(e)}")

        # Validate breed-species compatibility
        if (model.breed and model.breed.strip() and
            model.organism and model.organism.strip() and
            model.breed_term_source_id and model.breed_term_source_id.strip()):
            try:
                organism_term = convert_term(model.organism_term_source_id)
                breed_term = convert_term(model.breed_term_source_id)

                breed_errors = self.breed_validator.validate_breed_for_species(
                    organism_term, breed_term
                )
                if breed_errors:
                    errors.append(
                        f"Breed '{model.breed}' is not compatible with species '{model.organism}'"
                    )
            except Exception as e:
                errors.append(f"Error validating breed-species compatibility: {str(e)}")

        return errors

    def validate_with_pydantic(
        self,
        organisms: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate a list of organism samples"""

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

        # Validate each organism
        for i, org_data in enumerate(organisms):
            sample_name = org_data.get('Sample Name', f'organism_{i}')

            model, errors = self.validate_organism_sample(
                org_data,
                validate_relationships=False  # We'll do relationships separately
            )

            if model and not errors['errors']:
                results['valid_organisms'].append({
                    'index': i,
                    'sample_name': sample_name,
                    'model': model,
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

        # Validate relationships between organisms
        if results['valid_organisms']:
            relationship_errors = self.validate_relationships(
                [org['model'] for org in results['valid_organisms']],
                organisms
            )

            # Add relationship errors to results
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
        models: List[FAANGOrganismSample],
        raw_data: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """Validate parent-child relationships between organisms"""
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

            # Check maximum parents
            if len(model.child_of) > 2:
                sample_errors.append(f"Organism can have at most 2 parents, found {len(model.child_of)}")

            # Check each parent
            for parent_id in model.child_of:
                if parent_id == "restricted access":
                    continue

                if parent_id in sample_map:
                    parent_model = sample_map[parent_id]

                    # Check species match
                    if model.organism != parent_model.organism:
                        sample_errors.append(
                            f"Species mismatch: child is '{model.organism}' "
                            f"but parent '{parent_id}' is '{parent_model.organism}'"
                        )

                    # Check for circular relationships
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
    """Convert validated organism model to BioSample format"""

    def convert_term_to_url(term_id: str) -> str:
        """Convert term ID to proper URL format"""
        if not term_id or term_id == "restricted access":
            return ""
        term_colon = term_id.replace('_', ':', 1)
        return f"http://purl.obolibrary.org/obo/{term_colon.replace(':', '_')}"

    biosample_data = {
        "characteristics": {}
    }

    # Material
    biosample_data["characteristics"]["material"] = [{
        "text": model.material,
        "ontologyTerms": [convert_term_to_url(model.term_source_id)]
    }]

    # Organism
    biosample_data["characteristics"]["organism"] = [{
        "text": model.organism,
        "ontologyTerms": [convert_term_to_url(model.organism_term_source_id)]
    }]

    # Sex
    biosample_data["characteristics"]["sex"] = [{
        "text": model.sex,
        "ontologyTerms": [convert_term_to_url(model.sex_term_source_id)]
    }]

    # Birth date
    if model.birth_date and model.birth_date.strip():
        biosample_data["characteristics"]["birth date"] = [{
            "text": model.birth_date,
            "unit": model.birth_date_unit or ""
        }]

    # Breed
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
    # Relationships
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
    """Generate a human-readable validation report"""
    report = []
    report.append("FAANG Organism Validation Report")
    report.append("=" * 40)
    report.append(f"\nTotal organisms processed: {validation_results['summary']['total']}")
    report.append(f"Valid organisms: {validation_results['summary']['valid']}")
    report.append(f"Invalid organisms: {validation_results['summary']['invalid']}")
    report.append(f"Organisms with warnings: {validation_results['summary']['warnings']}")

    # Show validation errors
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

    # Show warnings and relationship issues
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
    new_json_data = {
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
        # "Breed": "Thoroughbred",
        # "Breed Term Source ID": "LBO_0000910",
        "health_status": [
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
    }

    sample_organisms = [new_json_data]

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