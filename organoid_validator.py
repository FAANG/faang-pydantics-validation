from typing import List, Dict, Any, Type, Optional, Tuple
from pydantic import BaseModel
from base_validator import BaseValidator
from generic_validator_classes import OntologyValidator
from rulesets_pydantics.organoid_ruleset import FAANGOrganoidSample
import json


class OrganoidValidator(BaseValidator):

    def _initialize_validators(self):
        self.ontology_validator = OntologyValidator(cache_enabled=True)

    def get_model_class(self) -> Type[BaseModel]:
        return FAANGOrganoidSample

    def get_sample_type_name(self) -> str:
        return "organoid"

    def validate_organoid_sample(
        self,
        data: Dict[str, Any],
        validate_relationships: bool = True,
        validate_with_json_schema: bool = True
    ) -> Tuple[Optional[FAANGOrganoidSample], Dict[str, List[str]]]:

        model, errors = self.validate_single_sample(data, validate_relationships)
        return model, errors

    def validate_with_pydantic(
        self,
        organoids: List[Dict[str, Any]],
        validate_relationships: bool = True,
        all_samples: Dict[str, List[Dict]] = None,
        validate_ontology_text: bool = True,
    ) -> Dict[str, Any]:

        return self.validate_samples(
            organoids,
            validate_relationships=validate_relationships,
            all_samples=all_samples,
            validate_ontology_text=validate_ontology_text
        )

    # validate organoids with relationship and ontology validation
    def validate_samples(
        self,
        samples: List[Dict[str, Any]],
        validate_relationships: bool = True,
        all_samples: Dict[str, List[Dict]] = None,
        validate_ontology_text: bool = True,
        **kwargs
    ) -> Dict[str, Any]:

        # base validation results
        results = super().validate_samples(samples, validate_relationships=False, all_samples=all_samples)

        # relationship validation
        if validate_relationships and all_samples:
            relationship_errors = self.validate_derived_from_relationships(samples, all_samples)

            # relationship checks for valid organoids
            for org in results['valid_organoids']:
                sample_name = org['sample_name']
                if sample_name in relationship_errors:
                    org['relationship_errors'] = relationship_errors[sample_name]
                    results['summary']['relationship_errors'] += 1

        # ontology text consistency validation
        if validate_ontology_text:
            text_consistency_errors = self.validate_ontology_text_consistency(samples)

            # text consistency errors as warnings for valid organoids
            for org in results['valid_organoids']:
                sample_name = org['sample_name']
                if sample_name in text_consistency_errors:
                    if 'ontology_warnings' not in org:
                        org['ontology_warnings'] = []
                    org['ontology_warnings'].extend(text_consistency_errors[sample_name])
                    results['summary']['warnings'] += 1

        return results

    def validate_derived_from_relationships(self, organoids: List[Dict[str, Any]],
                                            all_samples: Dict[str, List[Dict]] = None) -> Dict[str, List[str]]:

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

        # step 1: collect all relationships and materials
        if all_samples:
            for sample_type, samples in all_samples.items():
                for sample in samples:
                    sample_name = self._extract_sample_name(sample)
                    if sample_name:
                        relationships[sample_name] = {}

                        # get material type
                        material = self._extract_material(sample)
                        relationships[sample_name]['material'] = material

                        # get derived_from relationships
                        derived_from = self._extract_derived_from(sample)
                        if derived_from:
                            relationships[sample_name]['relationships'] = derived_from

        # step 2: validate relationships
        for sample_name, rel_info in relationships.items():
            if 'relationships' not in rel_info:
                continue

            current_material = rel_info['material']
            errors = []

            if any('restricted access' == ref for ref in rel_info['relationships']):
                continue

            for derived_from_ref in rel_info['relationships']:
                # check if referenced sample exists
                if derived_from_ref not in relationships:
                    errors.append(f"Relationships part: no entity '{derived_from_ref}' found")
                else:
                    # check material compatibility
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
        return sample.get('Sample Name', '')

    def _extract_material(self, sample: Dict) -> str:
        return sample.get('Material', '')

    def _extract_derived_from(self, sample: Dict) -> List[str]:
        derived_from_refs = []

        if 'Derived From' in sample:
            derived_from = sample['Derived From']
            if derived_from and derived_from.strip():
                derived_from_refs.append(derived_from.strip())

        if 'Child Of' in sample:
            child_of = sample['Child Of']
            if isinstance(child_of, list):
                for parent in child_of:
                    if parent and parent.strip():
                        derived_from_refs.append(parent.strip())
            elif child_of and child_of.strip():
                derived_from_refs.append(child_of.strip())

        return [ref for ref in derived_from_refs if ref and ref.strip()]

    def validate_ontology_text_consistency(self, organoids: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        ontology_data = self.collect_ontology_ids(organoids)
        text_consistency_errors = {}

        for i, organoid in enumerate(organoids):
            sample_name = organoid.get('Sample Name', f'organoid_{i}')
            errors = []

            # validate organ model text-term consistency
            organ_model_text = organoid.get('Organ Model')
            organ_model_term = organoid.get('Organ Model Term Source ID')
            if organ_model_text and organ_model_term and organ_model_term != "restricted access":
                error = self._check_text_term_consistency_flattened(
                    organ_model_text, organ_model_term, ontology_data, 'organ_model'
                )
                if error:
                    errors.append(error)

            # validate organ part model text-term consistency
            organ_part_text = organoid.get('Organ Part Model')
            organ_part_term = organoid.get('Organ Part Model Term Source ID')
            if organ_part_text and organ_part_term and organ_part_term != "restricted access":
                error = self._check_text_term_consistency_flattened(
                    organ_part_text, organ_part_term, ontology_data, 'organ_part_model'
                )
                if error:
                    errors.append(error)

            if errors:
                text_consistency_errors[sample_name] = errors

        return text_consistency_errors

    def collect_ontology_ids(self, organoids: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
        ids = set()

        for organoid in organoids:
            # get terms from organ model
            organ_model_term = organoid.get('Organ Model Term Source ID')
            if organ_model_term and organ_model_term != "restricted access":
                ids.add(organ_model_term)

            # get terms from organ part model
            organ_part_term = organoid.get('Organ Part Model Term Source ID')
            if organ_part_term and organ_part_term != "restricted access":
                ids.add(organ_part_term)

        return self.fetch_ontology_data_for_ids(ids)

    def fetch_ontology_data_for_ids(self, ids: set) -> Dict[str, List[Dict]]:
        results = {}

        for term_id in ids:
            if term_id and term_id != "restricted access":
                try:
                    # convert underscore to colon for OLS lookup
                    term_for_lookup = term_id.replace('_', ':', 1) if '_' in term_id else term_id
                    ols_data = self.ontology_validator.fetch_from_ols(term_for_lookup)
                    if ols_data:
                        results[term_id] = ols_data
                except Exception as e:
                    print(f"Error fetching ontology data for {term_id}: {e}")
                    results[term_id] = []

        return results

    def _check_text_term_consistency_flattened(self, text: str, term: str,
                                               ontology_data: Dict, field_name: str) -> str:
        if not text or not term or term == "restricted access":
            return None

        if term not in ontology_data:
            return f"Couldn't find term '{term}' in OLS"

        # determine ontology based on term prefix
        term_with_colon = term.replace('_', ':', 1) if '_' in term else term
        ontology_name = None
        if term_with_colon.startswith("UBERON:"):
            ontology_name = "UBERON"
        elif term_with_colon.startswith("BTO:"):
            ontology_name = "BTO"

        # get labels from OLS data
        term_labels = []
        for label_data in ontology_data[term]:
            if ontology_name and label_data.get('ontology_name', '').lower() == ontology_name.lower():
                term_labels.append(label_data.get('label', '').lower())
            elif not ontology_name:
                term_labels.append(label_data.get('label', '').lower())

        if not term_labels:
            return f"Couldn't find label in OLS with ontology name: {ontology_name}"

        # check if provided text matches any OLS label
        if str(text).lower() not in term_labels:
            return (f"Provided value '{text}' doesn't precisely match '{term_labels[0]}' "
                    f"for term '{term}' in field '{field_name}'")

        return None

    def export_to_biosample_format(self, model: FAANGOrganoidSample) -> Dict[str, Any]:

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
        biosample_data["characteristics"]["organ model"] = [{
            "text": model.organ_model,
            "ontologyTerms": [convert_term_to_url(model.organ_model_term_source_id)]
        }]

        # Organ part model (optional)
        if model.organ_part_model:
            biosample_data["characteristics"]["organ part model"] = [{
                "text": model.organ_part_model,
                "ontologyTerms": [convert_term_to_url(model.organ_part_model_term_source_id)]
            }]

        # Freezing method
        biosample_data["characteristics"]["freezing method"] = [{
            "text": model.freezing_method
        }]

        # Freezing date (if provided and not fresh)
        if model.freezing_date and model.freezing_date != "restricted access":
            biosample_data["characteristics"]["freezing date"] = [{
                "text": model.freezing_date,
                "unit": model.freezing_date_unit or ""
            }]

        # Organoid passage
        biosample_data["characteristics"]["organoid passage"] = [{
            "text": str(model.organoid_passage),
            "unit": model.organoid_passage_unit
        }]

        # Growth environment
        biosample_data["characteristics"]["growth environment"] = [{
            "text": model.growth_environment
        }]

        # Type of organoid culture
        biosample_data["characteristics"]["type of organoid culture"] = [{
            "text": model.type_of_organoid_culture
        }]

        # Organoid morphology (optional)
        if model.organoid_morphology:
            biosample_data["characteristics"]["organoid morphology"] = [{
                "text": model.organoid_morphology
            }]

        # Number of frozen cells (optional)
        if model.number_of_frozen_cells is not None:
            biosample_data["characteristics"]["number of frozen cells"] = [{
                "text": str(model.number_of_frozen_cells),
                "unit": model.number_of_frozen_cells_unit or "organoids"
            }]

        # Relationships - derived from
        biosample_data["relationships"] = [{
            "type": "derived from",
            "target": model.derived_from
        }]

        return biosample_data