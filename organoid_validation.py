from pydantic import ValidationError
from typing import List, Optional, Dict, Any, Tuple
import json
from organism_validator_classes import OntologyValidator

from rulesets_pydantics.organoid_ruleset import FAANGOrganoidSample


class OrganoidPydanticValidator:
    def __init__(self, schema_file_path: str = None):
        self.ontology_validator = OntologyValidator(cache_enabled=True)
        self.schema_file_path = schema_file_path or "faang_samples_organoid.metadata_rules.json"
        self._schema = None

    def get_recommended_fields(self, model_class) -> List[str]:
        """Extract recommended fields from pydantic model using metadata"""
        recommended_fields = []

        for field_name, field_info in model_class.model_fields.items():
            if (field_info.json_schema_extra and
                isinstance(field_info.json_schema_extra, dict) and
                field_info.json_schema_extra.get("recommended", False)):
                recommended_fields.append(field_name)

        return recommended_fields

    def validate_organoid_sample(
        self,
        data: Dict[str, Any],
        validate_relationships: bool = True,
        validate_with_json_schema: bool = True
    ) -> Tuple[Optional[FAANGOrganoidSample], Dict[str, List[str]]]:
        """
        Validate a single organoid sample
        """
        errors_dict = {
            'errors': [],
            'warnings': [],
            'field_errors': {}
        }

        # Pydantic validation
        try:
            organoid_model = FAANGOrganoidSample(**data)
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

        # Check recommended fields
        recommended_fields = self.get_recommended_fields(FAANGOrganoidSample)
        for field in recommended_fields:
            if getattr(organoid_model, field, None) is None:
                field_info = FAANGOrganoidSample.model_fields.get(field)
                field_display_name = field_info.alias if field_info and field_info.alias else field
                errors_dict['warnings'].append(
                    f"Field '{field_display_name}' is recommended but was not provided"
                )

        return organoid_model, errors_dict

    def validate_derived_from_relationships(self, organoids: List[Dict[str, Any]],
                                            all_samples: Dict[str, List[Dict]] = None) -> Dict[str, List[str]]:
        """
        Validate derived_from relationships based on Django RelationshipsIssues logic
        """
        # ALLOWED_RELATIONSHIPS mapping based on Django constants
        ALLOWED_RELATIONSHIPS = {
            'organoid': ['specimen from organism', 'cell culture', 'cell line'],
            'organism': ['organism'],  # organism can reference other organisms (parent-child)
            'specimen from organism': ['organism'],
            'cell culture': ['specimen from organism', 'organism'],
            'cell line': ['specimen from organism', 'organism'],
            'cell specimen': ['specimen from organism', 'organism'],
            'single cell specimen': ['specimen from organism', 'organism'],
            'pool of specimens': ['specimen from organism', 'organism']
        }

        relationship_errors = {}
        relationships = {}  # Store relationship info like Django version

        # Step 1: Collect all relationships and materials (similar to Django collect_relationships)
        if all_samples:
            for sample_type, samples in all_samples.items():
                for sample in samples:
                    sample_name = self._extract_sample_name(sample)
                    if sample_name:
                        relationships[sample_name] = {}

                        # Extract material type
                        material = self._extract_material(sample)
                        relationships[sample_name]['material'] = material

                        # Extract derived_from relationships
                        derived_from = self._extract_derived_from(sample)
                        if derived_from:
                            relationships[sample_name]['relationships'] = derived_from

        # Step 2: Validate relationships (similar to Django check_relationships)
        for sample_name, rel_info in relationships.items():
            if 'relationships' not in rel_info:
                continue

            current_material = rel_info['material']
            errors = []

            # Skip if restricted access
            if 'restricted access' in rel_info['relationships']:
                continue

            for derived_from_ref in rel_info['relationships']:
                # Check if referenced sample exists
                if derived_from_ref not in relationships:
                    errors.append(f"Relationships part: no entity '{derived_from_ref}' found")
                else:
                    # Check material compatibility
                    ref_material = relationships[derived_from_ref]['material']
                    allowed_materials = ALLOWED_RELATIONSHIPS.get(current_material, [])

                    if ref_material not in allowed_materials:
                        errors.append(
                            f"Relationships part: referenced entity '{derived_from_ref}' "
                            f"does not match condition 'should be {' or '.join(allowed_materials)}'"
                        )

                    # Additional check for organism parent-child relationships
                    if current_material == 'organism' and ref_material == 'organism':
                        self._check_organism_parent_child(sample_name, rel_info,
                                                          derived_from_ref, relationships[derived_from_ref],
                                                          errors, relationships)

            if errors:
                relationship_errors[sample_name] = errors

        return relationship_errors

    def _extract_sample_name(self, sample: Dict) -> str:
        """Extract sample name from various possible locations"""
        if 'custom' in sample and 'sample_name' in sample['custom']:
            return sample['custom']['sample_name']['value']
        elif 'Sample Name' in sample:
            return sample['Sample Name']
        return None

    def _extract_material(self, sample: Dict) -> str:
        """Extract material type from sample"""
        if 'Material' in sample:
            return sample['Material']
        elif 'samples_core' in sample and 'material' in sample['samples_core']:
            return sample['samples_core']['material']['text']
        return None

    def _extract_derived_from(self, sample: Dict) -> List[str]:
        """Extract derived_from references from sample"""
        derived_from_refs = []

        if 'derived_from' in sample:
            derived_from = sample['derived_from']
            if isinstance(derived_from, dict) and 'value' in derived_from:
                derived_from_refs.append(derived_from['value'])
            elif isinstance(derived_from, list):
                for item in derived_from:
                    if isinstance(item, dict) and 'value' in item:
                        derived_from_refs.append(item['value'])
                    elif isinstance(item, str):
                        derived_from_refs.append(item)
            elif isinstance(derived_from, str):
                derived_from_refs.append(derived_from)

        # Also check for 'child_of' relationship (for organisms)
        if 'Child Of' in sample:
            child_of = sample['Child Of']
            if isinstance(child_of, list):
                for parent in child_of:
                    if parent and parent.strip():
                        derived_from_refs.append(parent.strip())

        return [ref for ref in derived_from_refs if ref and ref.strip()]

    def _check_organism_parent_child(self, current_name: str, current_info: Dict,
                                     parent_name: str, parent_info: Dict,
                                     errors: List[str], all_relationships: Dict):
        """Check organism parent-child relationships (from Django check_parents)"""
        # Check if parent is also listing child as its parent (circular reference)
        if 'relationships' in parent_info and current_name in parent_info['relationships']:
            errors.append(f"Relationships part: parent '{parent_name}' is listing "
                          f"the child as its parent")

    def validate_with_pydantic(
        self,
        organoids: List[Dict[str, Any]],
        validate_relationships: bool = True,
        all_samples: Dict[str, List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Validate a list of organoid samples
        """
        results = {
            'valid_organoids': [],
            'invalid_organoids': [],
            'summary': {
                'total': len(organoids),
                'valid': 0,
                'invalid': 0,
                'warnings': 0,
                'relationship_errors': 0
            }
        }

        # Validate individual organoids
        for i, org_data in enumerate(organoids):
            sample_name = 'Unknown'
            if 'custom' in org_data and 'sample_name' in org_data['custom']:
                sample_name = org_data['custom']['sample_name']['value']
            elif 'Sample Name' in org_data:
                sample_name = org_data['Sample Name']
            else:
                sample_name = f'organoid_{i}'

            model, errors = self.validate_organoid_sample(
                org_data,
                validate_relationships=False
            )

            if model and not errors['errors']:
                results['valid_organoids'].append({
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
                results['invalid_organoids'].append({
                    'index': i,
                    'sample_name': sample_name,
                    'data': org_data,
                    'errors': errors
                })
                results['summary']['invalid'] += 1

        # Validate relationships between samples
        if validate_relationships and all_samples:
            relationship_errors = self.validate_derived_from_relationships(organoids, all_samples)

            # Add relationship errors to valid organoids
            for org in results['valid_organoids']:
                sample_name = org['sample_name']
                if sample_name in relationship_errors:
                    org['relationship_errors'] = relationship_errors[sample_name]
                    results['summary']['relationship_errors'] += 1

        return results


def export_organoid_to_biosample_format(model: FAANGOrganoidSample) -> Dict[str, Any]:
    """
    Export organoid model to BioSamples JSON format
    """

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

    # Material - should be organoid
    biosample_data["characteristics"]["material"] = [{
        "text": "organoid",
        "ontologyTerms": [convert_term_to_url("NCIT:C172259")]
    }]

    # Organ model
    if model.organ_model:
        biosample_data["characteristics"]["organ model"] = [{
            "text": model.organ_model.text,
            "ontologyTerms": [convert_term_to_url(model.organ_model.term)]
        }]

    # Organ part model (optional)
    if model.organ_part_model:
        biosample_data["characteristics"]["organ part model"] = [{
            "text": model.organ_part_model.text,
            "ontologyTerms": [convert_term_to_url(model.organ_part_model.term)]
        }]

    # Freezing method
    if model.freezing_method:
        biosample_data["characteristics"]["freezing method"] = [{
            "text": model.freezing_method.value
        }]

    # Freezing date (if provided and not fresh)
    if model.freezing_date and model.freezing_date.value != "restricted access":
        biosample_data["characteristics"]["freezing date"] = [{
            "text": model.freezing_date.value,
            "unit": model.freezing_date.units
        }]

    # Organoid passage
    if model.organoid_passage:
        biosample_data["characteristics"]["organoid passage"] = [{
            "text": str(model.organoid_passage.value),
            "unit": model.organoid_passage.units
        }]

    # Growth environment
    if model.growth_environment:
        biosample_data["characteristics"]["growth environment"] = [{
            "text": model.growth_environment.value
        }]

    # Type of organoid culture
    if model.type_of_organoid_culture:
        biosample_data["characteristics"]["type of organoid culture"] = [{
            "text": model.type_of_organoid_culture.value
        }]

    # Organoid morphology (optional)
    if model.organoid_morphology:
        biosample_data["characteristics"]["organoid morphology"] = [{
            "text": model.organoid_morphology.value
        }]

    # Relationships - derived from
    if model.derived_from:
        biosample_data["relationships"] = [{
            "type": "derived from",
            "target": model.derived_from.value
        }]

    return biosample_data


def generate_organoid_validation_report(validation_results: Dict[str, Any]) -> str:
    """
    Generate a human-readable validation report
    """
    report = []
    report.append("FAANG Organoid Validation Report")
    report.append("=" * 40)
    report.append(f"\nTotal organoids processed: {validation_results['summary']['total']}")
    report.append(f"Valid organoids: {validation_results['summary']['valid']}")
    report.append(f"Invalid organoids: {validation_results['summary']['invalid']}")
    report.append(f"Organoids with warnings: {validation_results['summary']['warnings']}")

    # Validation errors
    if validation_results['invalid_organoids']:
        report.append("\n\nValidation Errors:")
        report.append("-" * 20)
        for org in validation_results['invalid_organoids']:
            report.append(f"\nOrganoid: {org['sample_name']} (index: {org['index']})")
            for field, field_errors in org['errors'].get('field_errors', {}).items():
                for error in field_errors:
                    report.append(f"  ERROR in {field}: {error}")
            for error in org['errors'].get('errors', []):
                if not any(error.startswith(field) for field in org['errors'].get('field_errors', {})):
                    report.append(f"  ERROR: {error}")

    # Warnings and relationship issues
    if validation_results['valid_organoids']:
        warnings_found = False
        for org in validation_results['valid_organoids']:
            if org.get('warnings') or org.get('relationship_errors'):
                if not warnings_found:
                    report.append("\n\nWarnings and Non-Critical Issues:")
                    report.append("-" * 30)
                    warnings_found = True

                report.append(f"\nOrganoid: {org['sample_name']} (index: {org['index']})")
                for warning in org.get('warnings', []):
                    report.append(f"  WARNING: {warning}")
                for error in org.get('relationship_errors', []):
                    report.append(f"  RELATIONSHIP: {error}")

    return "\n".join(report)


if __name__ == "__main__":
    # Test with your provided data including cross-sample relationships
    json_string = '''
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
         ],
        "organoid": [
            {
                "Sample Name": "OCU_INRAE_S1",
                "sample_description": "Rabbit caecum organoid cell monolayer, cell culture insert 1 (immerged condition)",
                "Material": "organoid",
                "Term Source ID": "NCIT_C172259",
                "Project": "FAANG",
                "organ_model": {
                    "text": "Caecum",
                    "term": "UBERON:0001153",
                    "ontology_name": "UBERON"
                },
                "organ_part_model": {
                    "text": "Caecum epithelium",
                    "term": "UBERON:0005636",
                    "ontology_name": "UBERON"
                },
                "freezing_date": {
                    "value": "restricted access",
                    "units": "restricted access"
                },
                "freezing_method": {
                    "value": "fresh"
                },
                "freezing_protocol": {
                    "value": "restricted access"
                },
                "organoid_passage": {
                    "value": 2.0,
                    "units": "passages"
                },
                "organoid_passage_protocol": {
                    "value": "https://api.faang.org/files/protocols/samples/INRAE_SOP_METABOWEAN_20250206.pdf"
                },
                "organoid_culture_and_passage_protocol": {
                    "value": "https://api.faang.org/files/protocols/samples/INRAE_SOP_METABOWEAN_20250206.pdf"
                },
                "growth_environment": {
                    "value": "matrigel"
                },
                "type_of_organoid_culture": {
                    "value": "2D"
                },
                "derived_from": {
                    "value": "OCU_INRAE_PND18_S1"
                }
            },
            {
                "Sample Name": "OCU_INRAE_S2",
                "sample_description": "Rabbit caecum organoid cell monolayer, cell culture insert 2 (immerged condition)",
                "Material": "organoid",
                "Term Source ID": "NCIT_C172259",
                "Project": "FAANG",
                "organ_model": {
                    "text": "Caecum",
                    "term": "UBERON:0001153",
                    "ontology_name": "UBERON"
                },
                "organ_part_model": {
                    "text": "Caecum epithelium",
                    "term": "UBERON:0005636",
                    "ontology_name": "UBERON"
                },
                "freezing_date": {
                    "value": "restricted access",
                    "units": "restricted access"
                },
                "freezing_method": {
                    "value": "fresh"
                },
                "freezing_protocol": {
                    "value": "restricted access"
                },
                "organoid_passage": {
                    "value": 2.0,
                    "units": "passages"
                },
                "organoid_passage_protocol": {
                    "value": "https://api.faang.org/files/protocols/samples/INRAE_SOP_METABOWEAN_20250206.pdf"
                },
                "organoid_culture_and_passage_protocol": {
                    "value": "https://api.faang.org/files/protocols/samples/INRAE_SOP_METABOWEAN_20250206.pdf"
                },
                "growth_environment": {
                    "value": "matrigel"
                },
                "type_of_organoid_culture": {
                    "value": "2D"
                },
                "derived_from": {
                    "value": "OCU_INRAE_PND18_S1"
                }
            }
        ],
        "specimen_from_organism": [
        {
            "samples_core": {
                "sample_description": {
                    "value": "Adipose Tissue, H1"
                },
                "material": {
                    "text": "specimen from organism",
                    "term": "OBI:0001479"
                },
                "project": {
                    "value": "FAANG"
                }
            },
            "specimen_collection_date": {
                "value": "2005-05",
                "units": "YYYY-MM"
            },
            "geographic_location": {
                "value": "Denmark"
            },
            "animal_age_at_collection": {
                "value": 23.5,
                "units": "month"
            },
            "developmental_stage": {
                "text": "adult",
                "term": "EFO:0001272"
            },
            "health_status_at_collection": [
                {
                    "text": "normal",
                    "term": "PATO:0000461"
                }
            ],
            "organism_part": {
                "text": "adipose tissue",
                "term": "UBERON:0001013"
            },
            "specimen_collection_protocol": {
                "value": "ftp://ftp.faang.ebi.ac.uk/ftp/protocols/samples/WUR_SOP_animal_sampling_20160405.pdf"
            },
            "derived_from": {
                "value": "OCU_INRAE_PND18"
            },
            "custom": {
                "sample_name": {
                    "value": "OCU_INRAE_PND18_S1"
                }
            }
        }
    ]
    }
    '''

    data = json.loads(json_string)
    sample_organoids = data.get("organoid", [])

    validator = OrganoidPydanticValidator()

    # Pass all samples for cross-validation
    results = validator.validate_with_pydantic(
        sample_organoids,
        validate_relationships=True,
        all_samples=data  # Pass the entire dataset for cross-sample validation
    )

    report = generate_organoid_validation_report(results)
    print(report)

    # Export to BioSamples format if valid
    if results['valid_organoids']:
        for valid_org in results['valid_organoids']:
            biosample_data = export_organoid_to_biosample_format(valid_org['model'])
            print(f"\nBioSample format for {valid_org['sample_name']}:")
            print(json.dumps(biosample_data, indent=2))