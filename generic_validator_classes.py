from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field
import requests
import datetime

from constants import ELIXIR_VALIDATOR_URL, SPECIES_BREED_LINKS, ALLOWED_RELATIONSHIPS


class ValidationResult(BaseModel):
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    field_path: str
    value: Any = None


class ValidationConfig(BaseModel):
    """Configuration for validation behavior"""
    enable_external_biosample_validation: bool = True
    enable_relationship_chain_validation: bool = True
    enable_circular_reference_detection: bool = True
    enable_ols_text_validation: bool = True
    max_relationship_depth: int = 10
    api_timeout: int = 10
    treat_missing_biosamples_as_errors: bool = True


class OntologyValidator:
    def __init__(self, cache_enabled: bool = True):
        self.cache_enabled = cache_enabled
        self._cache: Dict[str, Any] = {}

    def validate_ontology_term(self, term: str, ontology_name: str,
                               allowed_classes: List[str],
                               text: str = None) -> ValidationResult:

        result = ValidationResult(field_path=f"{ontology_name}:{term}")

        if term == "restricted access":
            return result

        # check OLS for term and text validity
        ols_data = self.fetch_from_ols(term)
        if not ols_data:
            result.errors.append(f"Term {term} not found in OLS")
            return result

        if text:
            ols_labels = [doc.get('label', '').lower() for doc in ols_data
                          if doc.get('ontology_name', '').lower() == ontology_name.lower()]

            if not ols_labels:
                ols_labels = [doc.get('label', '').lower() for doc in ols_data]

            if text.lower() not in ols_labels:
                expected_label = ols_labels[0] if ols_labels else "unknown"
                result.warnings.append(
                    f"Provided value '{text}' doesn't precisely match '{expected_label}' "
                    f"for term '{term}'"
                )

        return result

    def fetch_from_ols(self, term_id: str) -> List[Dict]:
        if self.cache_enabled and term_id in self._cache:
            return self._cache[term_id]

        try:
            url = f"http://www.ebi.ac.uk/ols/api/search?q={term_id.replace(':', '_')}&rows=100"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            docs = data.get('response', {}).get('docs', [])
            if self.cache_enabled:
                self._cache[term_id] = docs
            return docs
        except Exception as e:
            print(f"Error fetching from OLS: {e}")
            return []

class BreedSpeciesValidator:

    def __init__(self, ontology_validator):
        self.ontology_validator = ontology_validator

    def validate_breed_for_species(self, organism_term: str, breed_term: str) -> List[str]:
        errors = []

        if organism_term not in SPECIES_BREED_LINKS:
            errors.append(f"Organism '{organism_term}' has no defined breed links.")
            return errors

        if breed_term in ["not applicable", "restricted access"]:
            return errors

        validation_result = self.ontology_validator.validate_ontology_term(
            term=breed_term,
            ontology_name="obo:lbo",
            allowed_classes=[SPECIES_BREED_LINKS[organism_term]],
            text=breed_term
        )
        if validation_result.errors:
            errors.append("Breed doesn't match the animal species")

        return errors


class RelationshipValidator:

    def __init__(self, config: ValidationConfig = None):
        self.config = config or ValidationConfig()
        self.biosamples_cache: Dict[str, Dict] = {}

    def validate_relationships(self, organisms: List[Dict[str, Any]]) -> Dict[str, ValidationResult]:
        """Original organism validation - kept for backward compatibility"""
        results = {}

        organism_map = {}
        for org in organisms:
            name = self.get_organism_identifier(org)
            organism_map[name] = org

        # BioSamples
        biosample_ids = set()
        for org in organisms:
            child_of = org.get('Child Of', [])
            if isinstance(child_of, str):
                child_of = [child_of]
            elif not isinstance(child_of, list):
                child_of = []

            for parent_id in child_of:
                if parent_id and parent_id.strip() and parent_id.startswith('SAM'):
                    biosample_ids.add(parent_id.strip())

        if biosample_ids and self.config.enable_external_biosample_validation:
            self.fetch_biosample_data(list(biosample_ids))

        # organism relationships
        for org in organisms:
            name = self.get_organism_identifier(org)
            result = ValidationResult(field_path=f"organism.{name}.child_of")

            child_of = org.get('Child Of', [])
            if isinstance(child_of, str):
                child_of = [child_of]
            elif not isinstance(child_of, list):
                child_of = []

            for parent_id in child_of:
                if not parent_id or not parent_id.strip():
                    continue

                parent_id = parent_id.strip()

                if parent_id == 'restricted access':
                    continue

                # check if parent exists
                if parent_id not in organism_map and parent_id not in self.biosamples_cache:
                    result.errors.append(
                        f"Relationships part: no entity '{parent_id}' found"
                    )
                    continue

                # parent data
                if parent_id in organism_map:
                    parent_data = organism_map[parent_id]
                    parent_species = parent_data.get('Organism', '')
                    parent_material = 'organism'
                else:
                    parent_data = self.biosamples_cache.get(parent_id, {})
                    parent_species = parent_data.get('organism', '')
                    parent_material = parent_data.get('material', '').lower()

                # species match
                current_species = org.get('Organism', '')

                if current_species and parent_species and current_species != parent_species:
                    result.errors.append(
                        f"Relationships part: the specie of the child '{current_species}' "
                        f"doesn't match the specie of the parent '{parent_species}'"
                    )

                # material type
                allowed_materials = ALLOWED_RELATIONSHIPS.get('organism', [])
                if parent_material and parent_material not in allowed_materials:
                    result.errors.append(
                        f"Relationships part: referenced entity '{parent_id}' "
                        f"does not match condition 'should be {' or '.join(allowed_materials)}'"
                    )

                # circular relationships
                if parent_id in organism_map:
                    parent_relationships = parent_data.get('Child Of', [])
                    if isinstance(parent_relationships, str):
                        parent_relationships = [parent_relationships]
                    elif not isinstance(parent_relationships, list):
                        parent_relationships = []

                    for grandparent_id in parent_relationships:
                        if grandparent_id and grandparent_id.strip() == name:
                            result.errors.append(
                                f"Relationships part: parent '{parent_id}' "
                                f"is listing the child as its parent"
                            )

            if result.errors or result.warnings:
                results[name] = result

        return results

    def validate_derived_from_relationships(self, all_samples: Dict[str, List[Dict]] = None) -> Dict[str, List[str]]:
        """
        Validate derived_from relationships across all sample types
        This method handles both 'Derived From' and 'Child Of' relationships
        Uses ALLOWED_RELATIONSHIPS from constants.py
        """

        relationship_errors = {}
        relationships = {}

        print("=== DEBUG: Available samples ===")
        if all_samples:
            for sample_type, samples in all_samples.items():
                sample_names = [s.get('Sample Name') for s in samples]
                print(f"{sample_type}: {sample_names}")
        else:
            print("all_samples is None!")
        print("================================")
        # Step 1: collect all relationships and materials
        if all_samples:
            for sample_type, samples in all_samples.items():
                for sample in samples:
                    sample_name = self._extract_sample_name(sample)
                    if sample_name:
                        relationships[sample_name] = {}

                        # get material type
                        material = self._extract_material(sample, sample_type)
                        relationships[sample_name]['material'] = material

                        # get derived_from relationships
                        derived_from = self._extract_derived_from(sample, sample_type)
                        if derived_from:
                            relationships[sample_name]['relationships'] = derived_from

        # Step 2: validate relationships
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
        """Extract sample name from flattened structures - updated for all sample types"""
        # All sample types now use the same flat structure
        return sample.get('Sample Name', '')

    def _extract_material(self, sample: Dict, sample_type: str) -> str:
        """Extract material from flattened structures - updated for all sample types"""
        # All sample types now use the same flat structure
        material = sample.get('Material', '')
        if material:
            return material

        # Fallback to sample type if Material field is missing
        return sample_type

    def _extract_derived_from(self, sample: Dict, sample_type: str) -> List[str]:
        """Extract derived_from/child_of references - updated for flattened structures"""
        refs = []

        # All specimen types now use 'Derived From' field
        if 'Derived From' in sample:
            derived_from = sample['Derived From']
            if derived_from and derived_from.strip():
                refs.append(derived_from.strip())

        # Organism samples use 'Child Of' field
        if 'Child Of' in sample:
            child_of = sample['Child Of']
            if isinstance(child_of, list):
                for parent in child_of:
                    if parent and parent.strip():
                        refs.append(parent.strip())
            elif child_of and child_of.strip():
                refs.append(child_of.strip())

        return [ref for ref in refs if ref and ref.strip()]

    def get_organism_identifier(self, organism: Dict) -> str:
        sample_name = organism.get('Sample Name', '')
        if sample_name and sample_name.strip():
            return sample_name.strip()
        return 'unknown'

    def fetch_biosample_data(self, biosample_ids: List[str]):
        """Fetch BioSample data synchronously with proper error handling"""
        for sample_id in biosample_ids:
            if sample_id in self.biosamples_cache:
                continue

            try:
                url = f"https://www.ebi.ac.uk/biosamples/samples/{sample_id}"
                response = requests.get(url, timeout=self.config.api_timeout)
                if response.status_code == 200:
                    data = response.json()
                    if 'error' not in data:
                        cache_entry = self._parse_biosample_response(data, sample_id)
                        self.biosamples_cache[sample_id] = cache_entry
                else:
                    print(f"BioSample {sample_id} returned status {response.status_code}")
            except Exception as e:
                print(f"Error fetching BioSample {sample_id}: {e}")

    def _parse_biosample_response(self, data: Dict, sample_id: str) -> Dict:
        """Parse BioSample API response"""
        cache_entry = {}

        characteristics = data.get('characteristics', {})
        if 'organism' in characteristics:
            cache_entry['organism'] = characteristics['organism'][0].get('text', '')

        if 'material' in characteristics:
            cache_entry['material'] = characteristics['material'][0].get('text', '')

        # relationships
        relationships = []
        for rel in data.get('relationships', []):
            if rel['source'] == sample_id and rel['type'] in ['child of', 'derived from']:
                relationships.append(rel['target'])
        cache_entry['relationships'] = relationships

        return cache_entry


class AdvancedValidationHelper:
    """Helper class for additional validation features"""

    @staticmethod
    def check_recommended_fields(sample_data: Dict, field_list: List[str]) -> List[str]:
        """Check for missing recommended fields"""
        warnings = []
        for field in field_list:
            if field not in sample_data or not sample_data[field]:
                warnings.append(f"Field '{field}' is recommended but was not provided")
        return warnings

    @staticmethod
    def check_missing_value_appropriateness(sample_data: Dict, field_classifications: Dict[str, str]) -> Dict[
        str, List[str]]:
        """Check if missing values are appropriate for field types - updated for flattened structure"""
        MISSING_VALUES = {
            'mandatory': {
                'errors': ["not applicable", "not collected", "not provided"],
                'warnings': ["restricted access"]
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

        issues = {'errors': {}, 'warnings': []}

        def check_field_value(field_name, field_data, field_type):
            # For flattened structure, check direct string values
            if isinstance(field_data, str):
                missing_config = MISSING_VALUES[field_type]
                if field_data in missing_config['errors']:
                    if field_name not in issues['errors']:
                        issues['errors'][field_name] = []
                    issues['errors'][field_name].append(
                        f"Field '{field_name}' contains inappropriate missing value '{field_data}'"
                    )
                elif field_data in missing_config['warnings']:
                    issues['warnings'].append(
                        f"Field '{field_name}' contains missing value '{field_data}' that may not be appropriate"
                    )
            # Handle list fields (like Health Status)
            elif isinstance(field_data, list):
                for item in field_data:
                    if isinstance(item, dict):
                        # Check nested values in list items
                        for key, value in item.items():
                            if isinstance(value, str):
                                missing_config = MISSING_VALUES[field_type]
                                if value in missing_config['errors']:
                                    if field_name not in issues['errors']:
                                        issues['errors'][field_name] = []
                                    issues['errors'][field_name].append(
                                        f"Field '{key}' in '{field_name}' contains inappropriate missing value"
                                    )
                                elif value in missing_config['warnings']:
                                    issues['warnings'].append(
                                        f"Field '{key}' in '{field_name}' contains missing value that may not be appropriate"
                                    )

        for field_name, field_value in sample_data.items():
            field_type = field_classifications.get(field_name, 'optional')
            check_field_value(field_name, field_value, field_type)

        return issues

    @staticmethod
    def check_date_unit_consistency(sample_data: Dict) -> Dict[str, List[str]]:
        """Check date-unit consistency - updated for flattened structure"""
        import datetime

        errors = {}

        # Check specimen collection date (now separate fields)
        specimen_date = sample_data.get('Specimen Collection Date')
        specimen_unit = sample_data.get('Unit')

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

        # Could add other date fields if needed in the future
        return errors