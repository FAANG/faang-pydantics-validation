import asyncio
import aiohttp
from typing import List, Dict, Any
from pydantic import BaseModel, Field
import requests

from constants import ELIXIR_VALIDATOR_URL, SPECIES_BREED_LINKS, ALLOWED_RELATIONSHIPS


class ValidationResult(BaseModel):
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    field_path: str
    value: Any = None


class OntologyValidator:
    def __init__(self, cache_enabled: bool = True, max_concurrent: int = 10):
        self.cache_enabled = cache_enabled
        self._cache: Dict[str, Any] = {}
        self.max_concurrent = max_concurrent
        self._semaphore = None

    def _get_semaphore(self):
        """Lazy initialization of semaphore"""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
        return self._semaphore

    def validate_ontology_term(self, term: str, ontology_name: str,
                               allowed_classes: List[str],
                               text: str = None) -> ValidationResult:
        result = ValidationResult(field_path=f"{ontology_name}:{term}")

        if term == "restricted access":
            return result

        # check OLS for term and text validity
        ols_data = self.fetch_from_ols_sync(term)
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

    def fetch_from_ols_sync(self, term_id: str) -> List[Dict]:
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

    async def fetch_from_ols_async(self, term_id: str) -> List[Dict]:
        """Async fetch for batch operations"""
        if self.cache_enabled and term_id in self._cache:
            return self._cache[term_id]

        semaphore = self._get_semaphore()
        async with semaphore:
            try:
                url = f"http://www.ebi.ac.uk/ols/api/search?q={term_id.replace(':', '_')}&rows=100"

                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                    async with session.get(url) as response:
                        response.raise_for_status()
                        data = await response.json()

                        docs = data.get('response', {}).get('docs', [])
                        if self.cache_enabled:
                            self._cache[term_id] = docs
                        return docs

            except Exception as e:
                print(f"Error fetching from OLS async: {e}")
                return []

    async def fetch_multiple_from_ols(self, term_ids: List[str]) -> Dict[str, List[Dict]]:
        """Fetch multiple terms concurrently"""
        tasks = []
        for term_id in term_ids:
            if term_id and term_id != "restricted access":
                tasks.append((term_id, self.fetch_from_ols_async(term_id)))

        if not tasks:
            return {}

        results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)

        output = {}
        for (term_id, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                print(f"Error fetching {term_id}: {result}")
                output[term_id] = []
            else:
                output[term_id] = result

        return output

    # Keep original method for backward compatibility
    def fetch_from_ols(self, term_id: str) -> List[Dict]:
        return self.fetch_from_ols_sync(term_id)


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
    def __init__(self, max_concurrent: int = 10):
        self.biosamples_cache: Dict[str, Dict] = {}
        self.max_concurrent = max_concurrent
        self._semaphore = None

    def _get_semaphore(self):
        """Lazy initialization of semaphore"""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
        return self._semaphore

    async def validate_relationships(self, organisms: List[Dict[str, Any]]) -> Dict[str, ValidationResult]:
        """Async validate relationships with concurrent BioSample fetching"""
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

        # Fetch BioSample data concurrently
        if biosample_ids:
            await self.fetch_biosample_data_batch(list(biosample_ids))

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

    def get_organism_identifier(self, organism: Dict) -> str:
        sample_name = organism.get('Sample Name', '')
        if sample_name and sample_name.strip():
            return sample_name.strip()
        return 'unknown'

    async def fetch_biosample_data_batch(self, biosample_ids: List[str]):
        """Fetch multiple BioSample records concurrently"""
        tasks = []
        for sample_id in biosample_ids:
            if sample_id not in self.biosamples_cache:
                tasks.append((sample_id, self.fetch_single_biosample(sample_id)))

        if not tasks:
            return

        results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)

        for (sample_id, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                print(f"Error fetching BioSample {sample_id}: {result}")
            elif result:
                self.biosamples_cache[sample_id] = result

    async def fetch_single_biosample(self, sample_id: str) -> Dict:
        """Fetch single BioSample with rate limiting"""
        semaphore = self._get_semaphore()
        async with semaphore:
            try:
                url = f"https://www.ebi.ac.uk/biosamples/samples/{sample_id}"

                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()

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
                        else:
                            print(f"HTTP {response.status} for BioSample {sample_id}")
                            return {}

            except Exception as e:
                print(f"Error fetching BioSample {sample_id}: {e}")
                return {}