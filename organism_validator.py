from typing import List, Dict, Any, Type, Tuple, Optional
from pydantic import BaseModel
from base_validator import BaseValidator
from generic_validator_classes import OntologyValidator, BreedSpeciesValidator, RelationshipValidator
from rulesets_pydantics.organism_ruleset import FAANGOrganismSample
import json


class OrganismValidator(BaseValidator):

    def _initialize_validators(self):
        self.ontology_validator = OntologyValidator(cache_enabled=True)
        self.breed_validator = BreedSpeciesValidator(self.ontology_validator)
        self.relationship_validator = RelationshipValidator()

    def get_model_class(self) -> Type[BaseModel]:
        return FAANGOrganismSample

    def get_sample_type_name(self) -> str:
        return "organism"

    def validate_organism_sample(
        self,
        data: Dict[str, Any],
        validate_relationships: bool = True,
        validate_with_json_schema: bool = True
    ) -> Tuple[Optional[FAANGOrganismSample], Dict[str, List[str]]]:

        model, errors = self.validate_single_sample(data, validate_relationships)
        return model, errors

    def validate_with_pydantic(
        self,
        organisms: List[Dict[str, Any]],
        validate_relationships: bool = True,
    ) -> Dict[str, Any]:

        return self.validate_samples(organisms, validate_relationships=validate_relationships)

    def validate_samples(
        self,
        samples: List[Dict[str, Any]],
        validate_relationships: bool = True,
        all_samples: Dict[str, List[Dict]] = None,
        **kwargs
    ) -> Dict[str, Any]:

        # base validation results
        results = super().validate_samples(samples, validate_relationships=False, all_samples=all_samples)

        # relationship validation for organisms
        if validate_relationships and results['valid_organisms']:
            valid_organism_data = [org['data'] for org in results['valid_organisms']]
            relationship_errors = self.relationship_validator.validate_relationships(
                valid_organism_data
            )

            # add relationship errors to results
            for org in results['valid_organisms']:
                sample_name = org['sample_name']
                if sample_name in relationship_errors:
                    org['relationship_errors'] = relationship_errors[sample_name].errors
                    if relationship_errors[sample_name].errors:
                        results['summary']['relationship_errors'] += 1

        return results

    def export_to_biosample_format(self, model: FAANGOrganismSample) -> Dict[str, Any]:

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

        # Health status
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