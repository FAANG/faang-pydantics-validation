from typing import List, Dict, Any, Type, Optional, Tuple
from pydantic import BaseModel
from base_validator import BaseValidator
from generic_validator_classes import OntologyValidator, RelationshipValidator
from rulesets_pydantics.teleostei_embryo_ruleset import FAANGTeleosteiEmbryoSample


class TeleosteiEmbryoValidator(BaseValidator):

    def _initialize_validators(self):
        self.ontology_validator = OntologyValidator(cache_enabled=True)
        self.relationship_validator = RelationshipValidator()

    def get_model_class(self) -> Type[BaseModel]:
        return FAANGTeleosteiEmbryoSample

    def get_sample_type_name(self) -> str:
        return "teleostei_embryo"

    def validate_teleostei_embryo_sample(
        self,
        data: Dict[str, Any],
        validate_relationships: bool = True,
    ) -> Tuple[Optional[FAANGTeleosteiEmbryoSample], Dict[str, List[str]]]:

        model, errors = self.validate_single_record(data)
        return model, errors

    def validate_with_pydantic(
        self,
        teleostei_embryos: List[Dict[str, Any]],
        validate_relationships: bool = True,
        all_samples: Dict[str, List[Dict]] = None,
        validate_ontology_text: bool = True,
    ) -> Dict[str, Any]:

        return self.validate_records(
            teleostei_embryos,
            validate_relationships=validate_relationships,
            all_samples=all_samples,
            validate_ontology_text=validate_ontology_text
        )

    def validate_records(
        self,
        sheet_records: List[Dict[str, Any]],
        validate_relationships: bool = True,
        all_samples: Dict[str, List[Dict]] = None,
        validate_ontology_text: bool = True,
        **kwargs
    ) -> Dict[str, Any]:

        # base validation results
        results = super().validate_records(sheet_records, validate_relationships=False, all_samples=all_samples)

        # relationship validation
        if validate_relationships and all_samples:
            relationship_errors = self.relationship_validator.validate_derived_from_relationships(all_samples)

            # relationship errors of valid teleostei embryos
            for embryo in results['valid_teleostei_embryos']:
                sample_name = embryo['sample_name']
                if sample_name in relationship_errors:
                    embryo['relationship_errors'] = relationship_errors[sample_name]
                    results['summary']['relationship_errors'] += 1

            # relationship errors for invalid teleostei embryos
            for embryo in results['invalid_teleostei_embryos']:
                sample_name = embryo['sample_name']
                if sample_name in relationship_errors:
                    if 'relationship_errors' not in embryo['errors']:
                        embryo['errors']['relationship_errors'] = []
                    embryo['errors']['relationship_errors'] = relationship_errors[sample_name]
                    results['summary']['relationship_errors'] += 1

        # Ontology text consistency validation (inherits specimen fields with ontology terms)
        if validate_ontology_text:
            text_consistency_errors = self.validate_ontology_text_consistency(sheet_records)

            # ontology warnings for valid embryos
            for embryo in results['valid_teleostei_embryos']:
                sample_name = embryo['sample_name']
                if sample_name in text_consistency_errors:
                    if 'ontology_warnings' not in embryo:
                        embryo['ontology_warnings'] = []
                    embryo['ontology_warnings'].extend(text_consistency_errors[sample_name])
                    results['summary']['warnings'] += 1

            # ontology warnings to invalid embryos
            for embryo in results['invalid_teleostei_embryos']:
                sample_name = embryo['sample_name']
                if sample_name in text_consistency_errors:
                    if 'ontology_warnings' not in embryo['errors']:
                        embryo['errors']['ontology_warnings'] = []
                    embryo['errors']['ontology_warnings'].extend(text_consistency_errors[sample_name])

        return results

    def validate_ontology_text_consistency(self, teleostei_embryos: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Validate ontology text consistency for specimen-related fields"""
        ontology_data = self.collect_ontology_ids(teleostei_embryos)
        text_consistency_errors = {}

        for i, embryo in enumerate(teleostei_embryos):
            sample_name = embryo.get('Sample Name', f'teleostei_embryo_{i}')
            errors = []

            # Validate developmental stage text-term consistency
            dev_stage_text = embryo.get('Developmental Stage')
            dev_stage_term = embryo.get('Developmental Stage Term Source ID')
            if dev_stage_text and dev_stage_term and dev_stage_term != "restricted access":
                error = self._check_text_term_consistency(
                    dev_stage_text, dev_stage_term, ontology_data, 'developmental_stage'
                )
                if error:
                    errors.append(error)

            # Validate organism part text-term consistency
            org_part_text = embryo.get('Organism Part')
            org_part_term = embryo.get('Organism Part Term Source ID')
            if org_part_text and org_part_term and org_part_term != "restricted access":
                error = self._check_text_term_consistency(
                    org_part_text, org_part_term, ontology_data, 'organism_part'
                )
                if error:
                    errors.append(error)

            if errors:
                text_consistency_errors[sample_name] = errors

        return text_consistency_errors

    def collect_ontology_ids(self, teleostei_embryos: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
        """Collect ontology IDs from specimen fields"""
        ids = set()

        for embryo in teleostei_embryos:
            # Get terms from developmental stage
            dev_stage_term = embryo.get('Developmental Stage Term Source ID')
            if dev_stage_term and dev_stage_term != "restricted access":
                ids.add(dev_stage_term)

            # Get terms from organism part
            org_part_term = embryo.get('Organism Part Term Source ID')
            if org_part_term and org_part_term != "restricted access":
                ids.add(org_part_term)

        return self.fetch_ontology_data_for_ids(ids)

    def fetch_ontology_data_for_ids(self, ids: set) -> Dict[str, List[Dict]]:
        """Fetch ontology data from OLS for given IDs"""
        results = {}

        for term_id in ids:
            if term_id and term_id != "restricted access":
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
                                     ontology_data: Dict, field_name: str) -> Optional[str]:
        """Check if provided text matches the ontology term label"""
        if not text or not term or term == "restricted access":
            return None

        if term not in ontology_data:
            return f"Couldn't find term '{term}' in OLS"

        # Determine ontology based on term prefix
        term_with_colon = term.replace('_', ':', 1) if '_' in term else term
        ontology_name = None
        if term_with_colon.startswith("EFO:"):
            ontology_name = "EFO"
        elif term_with_colon.startswith("UBERON:"):
            ontology_name = "UBERON"
        elif term_with_colon.startswith("BTO:"):
            ontology_name = "BTO"

        # Get labels from OLS data
        term_labels = []
        for label_data in ontology_data[term]:
            if ontology_name and label_data.get('ontology_name', '').lower() == ontology_name.lower():
                term_labels.append(label_data.get('label', '').lower())
            elif not ontology_name:
                term_labels.append(label_data.get('label', '').lower())

        if not term_labels:
            return f"Couldn't find label in OLS with ontology name: {ontology_name}"

        # Check if provided text matches any OLS label
        if str(text).lower() not in term_labels:
            return (f"Provided value '{text}' doesn't precisely match '{term_labels[0]}' "
                    f"for term '{term}' in field '{field_name}'")

        return None

    def export_to_biosample_format(self, model: FAANGTeleosteiEmbryoSample) -> Dict[str, Any]:
        """Export teleostei embryo model to BioSamples JSON format"""

        def convert_term_to_url(term_id: str) -> str:
            if not term_id or term_id in ["restricted access", "not applicable", "not collected", "not provided", ""]:
                return ""
            if '_' in term_id and ':' not in term_id:
                term_colon = term_id.replace('_', ':', 1)
            else:
                term_colon = term_id
            return f"http://purl.obolibrary.org/obo/{term_colon.replace(':', '_')}"

        # Start with the base specimen export
        biosample_data = {
            "characteristics": {}
        }

        # Material
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

        # Teleostei-specific fields
        biosample_data["characteristics"]["origin"] = [{
            "text": model.origin
        }]

        biosample_data["characteristics"]["reproductive strategy"] = [{
            "text": model.reproductive_strategy
        }]

        biosample_data["characteristics"]["hatching"] = [{
            "text": model.hatching
        }]

        biosample_data["characteristics"]["time post fertilisation"] = [{
            "text": str(model.time_post_fertilisation),
            "unit": model.time_post_fertilisation_unit
        }]

        biosample_data["characteristics"]["pre-hatching water temperature average"] = [{
            "text": str(model.pre_hatching_water_temperature_average),
            "unit": model.pre_hatching_water_temperature_average_unit
        }]

        biosample_data["characteristics"]["post-hatching water temperature average"] = [{
            "text": str(model.post_hatching_water_temperature_average),
            "unit": model.post_hatching_water_temperature_average_unit
        }]

        biosample_data["characteristics"]["degree days"] = [{
            "text": str(model.degree_days),
            "unit": model.degree_days_unit
        }]

        biosample_data["characteristics"]["growth media"] = [{
            "text": model.growth_media
        }]

        biosample_data["characteristics"]["medium replacement frequency"] = [{
            "text": str(model.medium_replacement_frequency),
            "unit": model.medium_replacement_frequency_unit
        }]

        biosample_data["characteristics"]["percentage total somite number"] = [{
            "text": str(model.percentage_total_somite_number),
            "unit": model.percentage_total_somite_number_unit
        }]

        biosample_data["characteristics"]["average water salinity"] = [{
            "text": str(model.average_water_salinity),
            "unit": model.average_water_salinity_unit
        }]

        biosample_data["characteristics"]["photoperiod"] = [{
            "text": model.photoperiod
        }]

        # Optional field
        if model.generations_from_wild is not None:
            biosample_data["characteristics"]["generations from wild"] = [{
                "text": str(model.generations_from_wild),
                "unit": model.generations_from_wild_unit or ""
            }]

        # Relationships - derived from
        biosample_data["relationships"] = [{
            "type": "derived from",
            "target": model.derived_from
        }]

        return biosample_data