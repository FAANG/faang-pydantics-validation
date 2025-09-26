from typing import List, Dict, Any, Type, Optional, Tuple
from pydantic import BaseModel
from base_validator import BaseValidator
from generic_validator_classes import (
    OntologyValidator, RelationshipValidator,
    AdvancedValidationHelper, ValidationConfig
)
from rulesets_pydantics.specimen_ruleset import FAANGSpecimenFromOrganismSample


class SpecimenValidator(BaseValidator):

    def _initialize_validators(self):
        self.config = ValidationConfig()
        self.ontology_validator = OntologyValidator(cache_enabled=True)
        self.relationship_validator = RelationshipValidator(self.config)
        self.validation_helper = AdvancedValidationHelper()

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

        # Enhanced validation for valid specimens
        for specimen in results['valid_specimen_from_organisms']:
            sample_name = specimen['sample_name']
            sample_data = specimen['data']

            # Check recommended fields
            recommended_warnings = self._check_recommended_fields(sample_data)
            if recommended_warnings:
                if 'warnings' not in specimen:
                    specimen['warnings'] = []
                specimen['warnings'].extend(recommended_warnings)
                results['summary']['warnings'] += len(recommended_warnings)

            # Check missing value appropriateness
            missing_value_issues = self._check_missing_value_appropriateness(sample_data)
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
            date_unit_errors = self._check_date_unit_consistency(sample_data)
            if date_unit_errors:
                if 'field_errors' not in specimen:
                    specimen['field_errors'] = {}
                specimen['field_errors'].update(date_unit_errors)
                results['summary']['invalid'] += len(date_unit_errors)

        # Simplified relationship validation using the generic method
        if validate_relationships and all_samples:
            relationship_errors = self.relationship_validator.validate_derived_from_relationships(all_samples)

            # Add relationship errors to specimens
            for specimen in results['valid_specimen_from_organisms']:
                sample_name = specimen['sample_name']
                if sample_name in relationship_errors:
                    specimen['relationship_errors'] = relationship_errors[sample_name]
                    results['summary']['relationship_errors'] += 1

        return results

    def _check_recommended_fields(self, sample_data: Dict[str, Any]) -> List[str]:
        """Check for missing recommended fields - updated for flattened structure"""
        recommended_fields = ['Health Status']  # Using the flat JSON field name
        return self.validation_helper.check_recommended_fields(sample_data, recommended_fields)

    def _check_missing_value_appropriateness(self, sample_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """Check if missing values are appropriate for field types - updated for flattened structure"""
        field_classifications = {
            'Specimen Collection Date': 'mandatory',
            'Geographic Location': 'mandatory',
            'Animal Age At Collection': 'mandatory',
            'Developmental Stage': 'mandatory',
            'Organism Part': 'mandatory',
            'Specimen Collection Protocol': 'mandatory',
            'Derived From': 'mandatory',
            'Health Status': 'recommended',
        }
        return self.validation_helper.check_missing_value_appropriateness(sample_data, field_classifications)

    def _check_date_unit_consistency(self, sample_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """Check date-unit consistency - updated for flattened structure"""
        import datetime

        errors = {}

        # Check specimen collection date consistency
        specimen_date = sample_data.get('Specimen Collection Date', '')
        specimen_unit = sample_data.get('Unit', '')

        if specimen_date and specimen_unit and specimen_date != "restricted access" and specimen_unit != "restricted access":
            unit_formats = {
                'YYYY-MM-DD': '%Y-%m-%d',
                'YYYY-MM': '%Y-%m',
                'YYYY': '%Y'
            }

            if specimen_unit in unit_formats:
                try:
                    datetime.datetime.strptime(specimen_date, unit_formats[specimen_unit])
                except ValueError:
                    errors['Specimen Collection Date'] = [
                        f"Date units '{specimen_unit}' should be consistent with date value '{specimen_date}'"
                    ]

        return errors

    def export_to_biosample_format(self, model: FAANGSpecimenFromOrganismSample) -> Dict[str, Any]:
        """Export specimen model to BioSamples JSON format - updated for flattened model"""

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
            "text": model.specimen_collection_date,
            "unit": model.specimen_collection_date_unit
        }]

        # Geographic location
        biosample_data["characteristics"]["geographic location"] = [{
            "text": model.geographic_location
        }]

        # Animal age at collection
        biosample_data["characteristics"]["animal age at collection"] = [{
            "text": str(model.animal_age_at_collection),
            "unit": model.animal_age_at_collection_unit
        }]

        # Developmental stage
        biosample_data["characteristics"]["developmental stage"] = [{
            "text": model.developmental_stage,
            "ontologyTerms": [convert_term_to_url(model.developmental_stage_term_source_id)]
        }]

        # Organism part
        biosample_data["characteristics"]["organism part"] = [{
            "text": model.organism_part,
            "ontologyTerms": [convert_term_to_url(model.organism_part_term_source_id)]
        }]

        # Specimen collection protocol
        biosample_data["characteristics"]["specimen collection protocol"] = [{
            "text": model.specimen_collection_protocol
        }]

        # Health status (optional)
        if model.health_status:
            biosample_data["characteristics"]["health status at collection"] = []
            for status in model.health_status:
                biosample_data["characteristics"]["health status at collection"].append({
                    "text": status.text,
                    "ontologyTerms": [convert_term_to_url(status.term)]
                })

        # Optional numeric fields
        if model.fasted_status:
            biosample_data["characteristics"]["fasted status"] = [{
                "text": model.fasted_status
            }]

        if model.number_of_pieces:
            biosample_data["characteristics"]["number of pieces"] = [{
                "text": str(model.number_of_pieces),
                "unit": model.number_of_pieces_unit
            }]

        if model.specimen_volume:
            biosample_data["characteristics"]["specimen volume"] = [{
                "text": str(model.specimen_volume),
                "unit": model.specimen_volume_unit
            }]

        if model.specimen_size:
            biosample_data["characteristics"]["specimen size"] = [{
                "text": str(model.specimen_size),
                "unit": model.specimen_size_unit
            }]

        if model.specimen_weight:
            biosample_data["characteristics"]["specimen weight"] = [{
                "text": str(model.specimen_weight),
                "unit": model.specimen_weight_unit
            }]

        if model.specimen_picture_url:
            biosample_data["characteristics"]["specimen picture url"] = [
                {"text": pic} for pic in model.specimen_picture_url
            ]

        if model.gestational_age_at_sample_collection:
            biosample_data["characteristics"]["gestational age at sample collection"] = [{
                "text": str(model.gestational_age_at_sample_collection),
                "unit": model.gestational_age_at_sample_collection_unit
            }]

        if model.average_incubation_temperature:
            biosample_data["characteristics"]["average incubation temperature"] = [{
                "text": str(model.average_incubation_temperature),
                "unit": model.average_incubation_temperature_unit
            }]

        if model.average_incubation_humidity:
            biosample_data["characteristics"]["average incubation humidity"] = [{
                "text": str(model.average_incubation_humidity),
                "unit": model.average_incubation_humidity_unit
            }]

        if model.embryonic_stage:
            biosample_data["characteristics"]["embryonic stage"] = [{
                "text": model.embryonic_stage,
                "unit": model.embryonic_stage_unit
            }]

        # Relationships - derived from
        biosample_data["relationships"] = [{
            "type": "derived from",
            "target": model.derived_from
        }]

        return biosample_data