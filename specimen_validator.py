from typing import List, Dict, Any, Type, Optional, Tuple
from pydantic import BaseModel
from base_validator import BaseValidator
from generic_validator_classes import OntologyValidator
from rulesets_pydantics.specimen_ruleset import FAANGSpecimenFromOrganismSample
import json


class SpecimenValidator(BaseValidator):

    def _initialize_validators(self):
        self.ontology_validator = OntologyValidator(cache_enabled=True)

    def get_model_class(self) -> Type[BaseModel]:
        return FAANGSpecimenFromOrganismSample

    def get_sample_type_name(self) -> str:
        return "specimen_from_organism"

    def validate_specimen_sample(
        self,
        data: Dict[str, Any],
        validate_relationships: bool = True,
        validate_with_json_schema: bool = True
    ) -> Tuple[Optional[FAANGSpecimenFromOrganismSample], Dict[str, List[str]]]:

        model, errors = self.validate_single_sample(data, validate_relationships)
        return model, errors

    def validate_with_pydantic(
        self,
        specimens: List[Dict[str, Any]],
        validate_relationships: bool = True,
        all_samples: Dict[str, List[Dict]] = None,
        validate_ontology_text: bool = True,
    ) -> Dict[str, Any]:

        return self.validate_samples(
            specimens,
            validate_relationships=validate_relationships,
            all_samples=all_samples,
            validate_ontology_text=validate_ontology_text
        )

    def validate_samples(
        self,
        samples: List[Dict[str, Any]],
        validate_relationships: bool = True,
        all_samples: Dict[str, List[Dict]] = None,
        validate_ontology_text: bool = True,
        **kwargs
    ) -> Dict[str, Any]:

        # Base validation results
        results = super().validate_samples(samples, validate_relationships=False, all_samples=all_samples)

        # Check recommended fields for valid specimens
        for specimen in results['valid_specimen_from_organisms']:
            recommended_warnings = self._check_recommended_fields_warnings(specimen['data'])
            if recommended_warnings:
                if 'warnings' not in specimen:
                    specimen['warnings'] = []
                specimen['warnings'].extend(recommended_warnings)
                results['summary']['warnings'] += len(recommended_warnings)

            # Check missing value appropriateness
            missing_value_issues = self._check_missing_value_appropriateness(specimen['data'])
            if missing_value_issues['errors']:
                if 'field_errors' not in specimen:
                    specimen['field_errors'] = {}
                specimen['field_errors'].update(missing_value_issues['errors'])
                results['summary']['invalid'] += len(missing_value_issues['errors'])
            if missing_value_issues['warnings']:
                if 'warnings' not in specimen:
                    specimen['warnings'] = []
                specimen['warnings'].extend(missing_value_issues['warnings'])
                results['summary']['warnings'] += len(missing_value_issues['warnings'])

            # Check date-unit consistency
            date_unit_errors = self._check_date_unit_consistency(specimen['data'])
            if date_unit_errors:
                if 'field_errors' not in specimen:
                    specimen['field_errors'] = {}
                specimen['field_errors'].update(date_unit_errors)
                results['summary']['invalid'] += len(date_unit_errors)

        # Relationship validation
        if validate_relationships and all_samples:
            relationship_errors = self.validate_derived_from_relationships(samples, all_samples)

            # Add relationship errors to valid specimens
            for specimen in results['valid_specimen_from_organisms']:
                sample_name = specimen['sample_name']
                if sample_name in relationship_errors:
                    specimen['relationship_errors'] = relationship_errors[sample_name]
                    results['summary']['relationship_errors'] += 1

        # Ontology text consistency validation
        if validate_ontology_text:
            text_consistency_errors = self.validate_ontology_text_consistency(samples)

            # Add text consistency errors as warnings for valid specimens
            for specimen in results['valid_specimen_from_organisms']:
                sample_name = specimen['sample_name']
                if sample_name in text_consistency_errors:
                    if 'ontology_warnings' not in specimen:
                        specimen['ontology_warnings'] = []
                    specimen['ontology_warnings'].extend(text_consistency_errors[sample_name])
                    results['summary']['warnings'] += len(text_consistency_errors[sample_name])

        return results

    def validate_derived_from_relationships(self, specimens: List[Dict[str, Any]],
                                            all_samples: Dict[str, List[Dict]] = None) -> Dict[str, List[str]]:
        """
        Validate derived_from relationships for specimen_from_organism samples
        """
        ALLOWED_RELATIONSHIPS = {
            'organoid': ['specimen from organism', 'cell culture', 'cell line'],
            'organism': ['organism'],
            'specimen from organism': ['organism'],
            'cell culture': ['specimen from organism', 'organism'],
            'cell line': ['specimen from organism', 'organism'],
            'cell specimen': ['specimen from organism', 'organism'],
            'single cell specimen': ['specimen from organism', 'organism'],
            'pool of specimens': ['specimen from organism', 'organism']
        }

        relationship_errors = {}
        relationships = {}

        # Step 1: Collect all relationships and materials from nested structure
        if all_samples:
            for sample_type, samples in all_samples.items():
                for sample in samples:
                    sample_name = self._extract_sample_name(sample)
                    if sample_name:
                        relationships[sample_name] = {}

                        # Extract material type from nested or flat structure
                        material = self._extract_material(sample)
                        relationships[sample_name]['material'] = material

                        # Extract derived_from relationships
                        derived_from = self._extract_derived_from(sample)
                        if derived_from:
                            relationships[sample_name]['relationships'] = derived_from

        # Step 2: Validate relationships
        for sample_name, rel_info in relationships.items():
            if 'relationships' not in rel_info:
                continue

            current_material = rel_info['material']
            errors = []

            # Skip if restricted access
            if any('restricted access' == ref for ref in rel_info['relationships']):
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

            if errors:
                relationship_errors[sample_name] = errors

        return relationship_errors

    def _extract_sample_name(self, sample: Dict) -> str:
        """Extract sample name from nested or flat structure"""
        # First try flat structure (for organism/organoid)
        if 'Sample Name' in sample:
            return sample['Sample Name']

        # Then try nested structure (for specimen_from_organism)
        if 'custom' in sample and 'sample_name' in sample['custom']:
            sample_name_data = sample['custom']['sample_name']
            if isinstance(sample_name_data, dict) and 'value' in sample_name_data:
                return sample_name_data['value']

        # Try samples_core structure
        if 'samples_core' in sample and 'sample_description' in sample['samples_core']:
            sample_desc = sample['samples_core']['sample_description']
            if isinstance(sample_desc, dict) and 'value' in sample_desc:
                return sample_desc['value']

        return ''

    def _extract_material(self, sample: Dict) -> str:
        """Extract material from nested or flat structure"""
        # First try flat structure
        if 'Material' in sample:
            return sample['Material']

        # Then try nested structure
        if 'samples_core' in sample and 'material' in sample['samples_core']:
            material_data = sample['samples_core']['material']
            if isinstance(material_data, dict) and 'text' in material_data:
                return material_data['text']

        return ''

    def _extract_derived_from(self, sample: Dict) -> List[str]:
        """Extract derived_from references from sample"""
        derived_from_refs = []

        # For specimen_from_organism (nested structure)
        if 'derived_from' in sample:
            derived_from = sample['derived_from']
            if isinstance(derived_from, dict) and 'value' in derived_from:
                value = derived_from['value']
                if value and value.strip():
                    derived_from_refs.append(value.strip())

        # For organoid samples (flat structure)
        if 'Derived From' in sample:
            derived_from = sample['Derived From']
            if derived_from and derived_from.strip():
                derived_from_refs.append(derived_from.strip())

        # For organism samples (Child Of relationship)
        if 'Child Of' in sample:
            child_of = sample['Child Of']
            if isinstance(child_of, list):
                for parent in child_of:
                    if parent and parent.strip():
                        derived_from_refs.append(parent.strip())
            elif child_of and child_of.strip():
                derived_from_refs.append(child_of.strip())

        return [ref for ref in derived_from_refs if ref and ref.strip()]

    def validate_ontology_text_consistency(self, specimens: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Validate that ontology text matches the official term labels from OLS
        """
        ontology_data = self.collect_ontology_ids(specimens)
        text_consistency_errors = {}

        for i, specimen in enumerate(specimens):
            sample_name = self._extract_sample_name(specimen)
            if not sample_name:
                sample_name = f'specimen_{i}'

            errors = []

            # Validate developmental stage text-term consistency
            dev_stage = specimen.get('developmental_stage', {})
            if isinstance(dev_stage, dict):
                dev_stage_text = dev_stage.get('text')
                dev_stage_term = dev_stage.get('term')
                if dev_stage_text and dev_stage_term and dev_stage_term != "restricted access":
                    error = self._check_text_term_consistency(
                        dev_stage_text, dev_stage_term, ontology_data, 'developmental_stage'
                    )
                    if error:
                        errors.append(error)

            # Validate organism part text-term consistency
            organism_part = specimen.get('organism_part', {})
            if isinstance(organism_part, dict):
                organism_part_text = organism_part.get('text')
                organism_part_term = organism_part.get('term')
                if organism_part_text and organism_part_term and organism_part_term != "restricted access":
                    error = self._check_text_term_consistency(
                        organism_part_text, organism_part_term, ontology_data, 'organism_part'
                    )
                    if error:
                        errors.append(error)

            # Validate health status text-term consistency
            health_status = specimen.get('health_status_at_collection', [])
            if isinstance(health_status, list):
                for j, status in enumerate(health_status):
                    if isinstance(status, dict):
                        status_text = status.get('text')
                        status_term = status.get('term')
                        if (status_text and status_term and
                            status_term not in ["not applicable", "not collected", "not provided",
                                                "restricted access"]):
                            error = self._check_text_term_consistency(
                                status_text, status_term, ontology_data, f'health_status_at_collection[{j}]'
                            )
                            if error:
                                errors.append(error)

            if errors:
                text_consistency_errors[sample_name] = errors

        return text_consistency_errors

    def collect_ontology_ids(self, specimens: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
        """
        Collect all ontology term IDs from specimens for OLS validation
        """
        ids = set()

        for specimen in specimens:
            # Extract terms from developmental stage
            dev_stage = specimen.get('developmental_stage', {})
            if isinstance(dev_stage, dict):
                dev_stage_term = dev_stage.get('term')
                if dev_stage_term and dev_stage_term != "restricted access":
                    ids.add(dev_stage_term)

            # Extract terms from organism part
            organism_part = specimen.get('organism_part', {})
            if isinstance(organism_part, dict):
                organism_part_term = organism_part.get('term')
                if organism_part_term and organism_part_term != "restricted access":
                    ids.add(organism_part_term)

            # Extract terms from health status
            health_status = specimen.get('health_status_at_collection', [])
            if isinstance(health_status, list):
                for status in health_status:
                    if isinstance(status, dict):
                        status_term = status.get('term')
                        if (status_term and
                            status_term not in ["not applicable", "not collected", "not provided",
                                                "restricted access"]):
                            ids.add(status_term)

        # Fetch ontology data from OLS
        return self.fetch_ontology_data_for_ids(ids)

    def fetch_ontology_data_for_ids(self, ids: set) -> Dict[str, List[Dict]]:
        """
        Fetch ontology data from OLS for given term IDs
        """
        results = {}

        for term_id in ids:
            if term_id and term_id not in ["restricted access", "not applicable", "not collected", "not provided"]:
                try:
                    # Convert underscore to colon for OLS lookup
                    term_for_lookup = term_id.replace('_', ':', 1) if '_' in term_id else term_id
                    ols_data = self.ontology_validator.fetch_from_ols(term_for_lookup)
                    if ols_data:
                        results[term_id] = ols_data
                except Exception as e:
                    print(f"Error fetching ontology data for {term_id}: {e}")
                    results[term_id] = []

        return results

    def _check_text_term_consistency(self, text: str, term: str,
                                     ontology_data: Dict, field_name: str) -> str:
        """
        Check if text matches term label from OLS with enhanced validation
        Based on Django's WarningsAndAdditionalChecks.check_ols()
        """
        if not text or not term or term in ["restricted access", "not applicable", "not collected", "not provided"]:
            return None

    def _validate_biosample_id_format(self, sample_id: str) -> bool:
        """
        Validate BioSample ID format
        Based on Django's update_utils.check_biosampleid()
        """
        import re

        if not sample_id:
            return False

        # BioSample accessions: SAM[AED][AG]?\d+
        pattern = r"^SAM[AED][AG]?\d+$"
        return bool(re.search(pattern, sample_id.upper()))

    def _check_biosample_references(self, sample_data: Dict[str, Any]) -> List[str]:
        """
        Check if BioSample ID references are valid format
        This is used when derived_from contains BioSample IDs
        """
        errors = []

        # Check derived_from field for BioSample IDs
        derived_from = sample_data.get('derived_from', {})
        if isinstance(derived_from, dict) and 'value' in derived_from:
            value = derived_from['value']
            if value and 'SAM' in value.upper():
                if not self._validate_biosample_id_format(value):
                    errors.append(f"Invalid BioSample ID format: {value}")

        return errors

        # Convert term format for lookup
        term_with_colon = term.replace('_', ':', 1) if '_' in term else term

        if term not in ontology_data:
            return f"Couldn't find term '{term}' in OLS"

        # Determine expected ontology based on term prefix and field
        expected_ontologies = []
        if term_with_colon.startswith("EFO:"):
            expected_ontologies = ["efo"]
        elif term_with_colon.startswith("UBERON:"):
            expected_ontologies = ["uberon"]
        elif term_with_colon.startswith("BTO:"):
            expected_ontologies = ["bto"]
        elif term_with_colon.startswith("PATO:"):
            expected_ontologies = ["pato"]

        # Additional field-specific ontology expectations
        if field_name == 'developmental_stage':
            expected_ontologies = ["efo", "uberon"]
        elif field_name == 'organism_part':
            expected_ontologies = ["uberon", "bto"]
        elif 'health_status' in field_name:
            expected_ontologies = ["pato", "efo"]

        # Get labels from OLS data matching expected ontologies
        term_labels = []
        for label_data in ontology_data[term]:
            ontology_name = label_data.get('ontology_name', '').lower()
            if not expected_ontologies or ontology_name in expected_ontologies:
                label = label_data.get('label', '').lower()
                if label:  # Only add non-empty labels
                    term_labels.append(label)

        if not term_labels:
            ontology_list = ', '.join(expected_ontologies) if expected_ontologies else 'any'
            return f"Couldn't find label in OLS with ontology name(s): {ontology_list}"

        # Check if provided text matches any OLS label (case-insensitive)
        text_lower = str(text).lower()
        if text_lower not in term_labels:
            best_match = term_labels[0] if term_labels else 'unknown'
            return (f"Provided value '{text}' doesn't precisely match '{best_match}' "
                    f"for term '{term}' in field '{field_name}'")

        return None

    def export_to_biosample_format(self, model: FAANGSpecimenFromOrganismSample) -> Dict[str, Any]:
        """
        Export specimen model to BioSamples JSON format
        """

        def convert_term_to_url(term_id: str) -> str:
            if not term_id or term_id in ["restricted access", "not applicable", "not collected", "not provided", ""]:
                return ""
            if '_' in term_id and ':' not in term_id:
                term_colon = term_id.replace('_', ':', 1)
            else:
                term_colon = term_id
            return f"http://purl.obolibrary.org/obo/{term_colon.replace(':', '_')}"

        biosample_data = {
            "characteristics": {}
        }

        # Material - should be specimen from organism
        biosample_data["characteristics"]["material"] = [{
            "text": model.material,
            "ontologyTerms": [convert_term_to_url(model.term_source_id)]
        }]

        # Specimen collection date
        biosample_data["characteristics"]["specimen collection date"] = [{
            "text": model.specimen_collection_date.value,
            "unit": model.specimen_collection_date.units
        }]

        # Geographic location
        biosample_data["characteristics"]["geographic location"] = [{
            "text": model.geographic_location.value
        }]

        # Animal age at collection
        biosample_data["characteristics"]["animal age at collection"] = [{
            "text": str(model.animal_age_at_collection.value),
            "unit": model.animal_age_at_collection.units
        }]

        # Developmental stage
        biosample_data["characteristics"]["developmental stage"] = [{
            "text": model.developmental_stage.text,
            "ontologyTerms": [convert_term_to_url(model.developmental_stage.term)]
        }]

        # Organism part
        biosample_data["characteristics"]["organism part"] = [{
            "text": model.organism_part.text,
            "ontologyTerms": [convert_term_to_url(model.organism_part.term)]
        }]

        # Specimen collection protocol
        biosample_data["characteristics"]["specimen collection protocol"] = [{
            "text": model.specimen_collection_protocol.value
        }]

        # Health status at collection (optional)
        if model.health_status_at_collection:
            biosample_data["characteristics"]["health status at collection"] = []
            for status in model.health_status_at_collection:
                biosample_data["characteristics"]["health status at collection"].append({
                    "text": status.text,
                    "ontologyTerms": [convert_term_to_url(status.term)]
                })

        # Optional numeric fields
        if model.fasted_status:
            biosample_data["characteristics"]["fasted status"] = [{
                "text": model.fasted_status.value
            }]

        if model.number_of_pieces:
            biosample_data["characteristics"]["number of pieces"] = [{
                "text": str(model.number_of_pieces.value),
                "unit": model.number_of_pieces.units
            }]

        if model.specimen_volume:
            biosample_data["characteristics"]["specimen volume"] = [{
                "text": str(model.specimen_volume.value),
                "unit": model.specimen_volume.units
            }]

        if model.specimen_size:
            biosample_data["characteristics"]["specimen size"] = [{
                "text": str(model.specimen_size.value),
                "unit": model.specimen_size.units
            }]

        if model.specimen_weight:
            biosample_data["characteristics"]["specimen weight"] = [{
                "text": str(model.specimen_weight.value),
                "unit": model.specimen_weight.units
            }]

        if model.specimen_picture_url:
            biosample_data["characteristics"]["specimen picture url"] = [
                {"text": pic.value} for pic in model.specimen_picture_url
            ]

        if model.gestational_age_at_sample_collection:
            biosample_data["characteristics"]["gestational age at sample collection"] = [{
                "text": str(model.gestational_age_at_sample_collection.value),
                "unit": model.gestational_age_at_sample_collection.units
            }]

        if model.average_incubation_temperature:
            biosample_data["characteristics"]["average incubation temperature"] = [{
                "text": str(model.average_incubation_temperature.value),
                "unit": model.average_incubation_temperature.units
            }]

        if model.average_incubation_humidity:
            biosample_data["characteristics"]["average incubation humidity"] = [{
                "text": str(model.average_incubation_humidity.value),
                "unit": model.average_incubation_humidity.units
            }]

        if model.embryonic_stage:
            biosample_data["characteristics"]["embryonic stage"] = [{
                "text": model.embryonic_stage.value,
                "unit": model.embryonic_stage.units
            }]

        # Relationships - derived from
        biosample_data["relationships"] = [{
            "type": "derived from",
            "target": model.derived_from.value
        }]

        return biosample_data

    def _check_recommended_fields_warnings(self, sample_data: Dict[str, Any]) -> List[str]:
        """
        Check for missing recommended fields and return warnings
        Based on Django's WarningsAndAdditionalChecks.check_recommended_fields()
        """
        warnings = []

        # Check if health_status_at_collection is missing (it's recommended)
        if 'health_status_at_collection' not in sample_data or not sample_data['health_status_at_collection']:
            warnings.append("Field 'health_status_at_collection' is recommended but was not provided")

        return warnings

    def _check_missing_value_appropriateness(self, sample_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Check if missing values are appropriate for field types
        Based on Django's WarningsAndAdditionalChecks.check_missing_values()
        """
        # Missing values configuration from Django constants.py
        MISSING_VALUES = {
            'mandatory': {
                'errors': ["not applicable", "not collected", "not provided"],
                "warnings": ["restricted access"]
            },
            'recommended': {
                'errors': [],
                'warnings': ["not collected", "not provided"]
            },
            'optional': {
                'errors': [],
                'warnings': []
            }
        }

        # Field classification (based on JSON schema)
        MANDATORY_FIELDS = [
            'specimen_collection_date', 'geographic_location', 'animal_age_at_collection',
            'developmental_stage', 'organism_part', 'specimen_collection_protocol', 'derived_from'
        ]
        RECOMMENDED_FIELDS = ['health_status_at_collection']

        issues = {'errors': {}, 'warnings': []}

        def check_field_value(field_name, field_data, field_type):
            if isinstance(field_data, dict):
                for key, value in field_data.items():
                    if isinstance(value, str):
                        missing_config = MISSING_VALUES[field_type]
                        if value in missing_config['errors']:
                            error_msg = f"Field '{key}' of '{field_name}' contains missing value that is not appropriate for this field"
                            if field_name not in issues['errors']:
                                issues['errors'][field_name] = []
                            issues['errors'][field_name].append(error_msg)
                        elif value in missing_config['warnings']:
                            warning_msg = f"Field '{key}' of '{field_name}' contains missing value that is not appropriate for this field"
                            issues['warnings'].append(warning_msg)
            elif isinstance(field_data, list):
                for item in field_data:
                    check_field_value(field_name, item, field_type)

        # Check all fields
        for field_name, field_value in sample_data.items():
            if field_name in MANDATORY_FIELDS:
                check_field_value(field_name, field_value, 'mandatory')
            elif field_name in RECOMMENDED_FIELDS:
                check_field_value(field_name, field_value, 'recommended')
            else:
                check_field_value(field_name, field_value, 'optional')

        return issues

    def _check_date_unit_consistency(self, sample_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Check that date values are consistent with their units
        Based on Django's WarningsAndAdditionalChecks.check_date_units()
        """
        import datetime

        errors = {}

        def validate_date_field(field_name, field_data):
            if isinstance(field_data, dict) and 'value' in field_data and 'units' in field_data:
                if 'date' in field_name.lower():  # Only check date-related fields
                    value = field_data['value']
                    units = field_data['units']

                    if value == "restricted access" or units == "restricted access":
                        return

                    # Map units to datetime format
                    unit_formats = {
                        'YYYY-MM-DD': '%Y-%m-%d',
                        'YYYY-MM': '%Y-%m',
                        'YYYY': '%Y'
                    }

                    if units in unit_formats:
                        try:
                            datetime.datetime.strptime(value, unit_formats[units])
                        except ValueError:
                            error_msg = f"Date units: {units} should be consistent with date value: {value}"
                            if field_name not in errors:
                                errors[field_name] = []
                            errors[field_name].append(error_msg)

        # Check all fields for date consistency
        for field_name, field_value in sample_data.items():
            validate_date_field(field_name, field_value)

        return errors

    def get_recommended_fields(self, model_class) -> List[str]:
        """Extract recommended fields from pydantic model using metadata"""
        recommended_fields = []

        for field_name, field_info in model_class.model_fields.items():
            if (field_info.json_schema_extra and
                isinstance(field_info.json_schema_extra, dict) and
                field_info.json_schema_extra.get("recommended", False)):
                recommended_fields.append(field_name)

        return recommended_fields