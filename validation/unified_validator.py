from typing import Dict, List, Any
from validation.sample.teleostei_embryo_validator import TeleosteiEmbryoValidator
from validation.sample.organism_validator import OrganismValidator
from validation.sample.organoid_validator import OrganoidValidator
from validation.sample.specimen_validator import SpecimenValidator
from validation.sample.teleostei_post_hatching_validator import TeleosteiPostHatchingValidator
from validation.sample.single_cell_specimen_validator import SingleCellSpecimenValidator
from validation.sample.pool_of_specimens_validator import PoolOfSpecimensValidator
from validation.sample.cell_specimen_validator import CellSpecimenValidator
from validation.sample.cell_culture_validator import CellCultureValidator
from validation.sample.cell_line_validator import CellLineValidator
from validation.sample.metadata_validator import SubmissionValidator, PersonValidator, OrganizationValidator, \
    AnalysisSubmissionValidator
from validation.analysis.analysis_validator import (
    ENAAnalysisValidator,
    EVAAnalysisValidator,
    FAANGAnalysisValidator
)
from validation.generic_validator_classes import (
    collect_ontology_terms_from_data,
    OntologyValidator,
    RelationshipValidator
)


class UnifiedFAANGValidator:
    def __init__(self):
        # shared validator instances for samples
        self.shared_ontology_validator = OntologyValidator(cache_enabled=True)
        self.shared_relationship_validator = RelationshipValidator()

        # sample validators - pass shared instances
        self.sample_validators = {
            'organism': OrganismValidator(
                ontology_validator=self.shared_ontology_validator,
                relationship_validator=self.shared_relationship_validator
            ),
            'organoid': OrganoidValidator(
                ontology_validator=self.shared_ontology_validator,
                relationship_validator=self.shared_relationship_validator
            ),
            'specimen from organism': SpecimenValidator(
                ontology_validator=self.shared_ontology_validator,
                relationship_validator=self.shared_relationship_validator
            ),
            'teleostei embryo': TeleosteiEmbryoValidator(
                ontology_validator=self.shared_ontology_validator,
                relationship_validator=self.shared_relationship_validator
            ),
            'teleostei post-hatching': TeleosteiPostHatchingValidator(
                ontology_validator=self.shared_ontology_validator,
                relationship_validator=self.shared_relationship_validator
            ),
            'single cell specimen': SingleCellSpecimenValidator(
                ontology_validator=self.shared_ontology_validator,
                relationship_validator=self.shared_relationship_validator
            ),
            'pool of specimens': PoolOfSpecimensValidator(
                ontology_validator=self.shared_ontology_validator,
                relationship_validator=self.shared_relationship_validator
            ),
            'cell specimen': CellSpecimenValidator(
                ontology_validator=self.shared_ontology_validator,
                relationship_validator=self.shared_relationship_validator
            ),
            'cell culture': CellCultureValidator(
                ontology_validator=self.shared_ontology_validator,
                relationship_validator=self.shared_relationship_validator
            ),
            'cell line': CellLineValidator(
                ontology_validator=self.shared_ontology_validator,
                relationship_validator=self.shared_relationship_validator
            )
        }
        self.supported_sample_types = set(self.sample_validators.keys())

        # metadata validators - samples
        self.metadata_validators = {
            'submission': SubmissionValidator(),
            'person': PersonValidator(),
            'organization': OrganizationValidator()
        }
        self.supported_metadata_types = set(self.metadata_validators.keys())

        # metadata validators - analyses
        self.analysis_metadata_validators = {
            'submission': AnalysisSubmissionValidator(),
        }
        self.supported_analysis_metadata_types = set(self.analysis_metadata_validators.keys())


        # analysis validators
        self.analysis_validators = {
            'ena': ENAAnalysisValidator(),
            'eva': EVAAnalysisValidator(),
            'faang': FAANGAnalysisValidator()
        }
        self.supported_analysis_types = set(self.analysis_validators.keys())

    def prefetch_all_ontology_terms(self, data: Dict[str, List[Dict[str, Any]]]):
        # collect unique term IDs
        term_ids = collect_ontology_terms_from_data(data)

        if not term_ids:
            print("No ontology terms to pre-fetch")
            return

        # shared ontology validator
        self.shared_ontology_validator.batch_fetch_from_ols_sync(list(term_ids))
        print(f"Pre-fetch complete. Cache now contains {len(self.shared_ontology_validator._cache)} terms.")

    # async version for use in FastAPI endpoints
    async def prefetch_all_ontology_terms_async(self, data: Dict[str, List[Dict[str, Any]]]):
        # collect unique term IDs
        term_ids = collect_ontology_terms_from_data(data)

        if not term_ids:
            print("No ontology terms to pre-fetch")
            return

        # Use shared ontology validator
        result = await self.shared_ontology_validator.batch_fetch_from_ols(list(term_ids))
        self.shared_ontology_validator._cache.update(result)
        print(f"Pre-fetch complete. Cache now contains {len(self.shared_ontology_validator._cache)} terms.")

    def prefetch_all_biosample_ids(self, data: Dict[str, List[Dict[str, Any]]]):
        # shared relationship validator
        biosample_ids = self.shared_relationship_validator.collect_biosample_ids_from_samples(data)

        if not biosample_ids:
            print("No BioSample IDs to pre-fetch")
            return

        print(f"Found {len(biosample_ids)} BioSample IDs to fetch")

        # fetch all BioSample IDs concurrently
        self.shared_relationship_validator.batch_fetch_biosamples_sync(list(biosample_ids))

        print(
            f"Pre-fetch complete. BioSample cache now contains {len(self.shared_relationship_validator.biosamples_cache)} entries.")

    # async version for FastAPI endpoint
    async def prefetch_all_biosample_ids_async(self, data: Dict[str, List[Dict[str, Any]]]):
        # shared relationship validator
        biosample_ids = self.shared_relationship_validator.collect_biosample_ids_from_samples(data)

        if not biosample_ids:
            print("No BioSample IDs to pre-fetch")
            return

        print(f"Found {len(biosample_ids)} BioSample IDs to fetch")

        # fetch all BioSample IDs concurrently using async method
        result = await self.shared_relationship_validator.batch_fetch_biosamples(list(biosample_ids))
        self.shared_relationship_validator.biosamples_cache.update(result)

        print(
            f"Pre-fetch complete. BioSample cache now contains {len(self.shared_relationship_validator.biosamples_cache)} entries.")

    def validate_all_records(
        self,
        data: Dict[str, List[Dict[str, Any]]],
        validate_relationships: bool = True,
        validate_ontology_text: bool = True
    ) -> Dict[str, Any]:

        all_results = {
            'sample_types_processed': [],
            'metadata_types_processed': [],
            'analysis_types_processed': [],
            'total_summary': {
                'total_samples': 0,
                'valid_samples': 0,
                'invalid_samples': 0,
                'warnings': 0,
                'relationship_errors': 0
            },
            'metadata_summary': {
                'total_metadata': 0,
                'valid_metadata': 0,
                'invalid_metadata': 0
            },
            'analysis_summary': {
                'total_analyses': 0,
                'valid_analyses': 0,
                'invalid_analyses': 0,
                'warnings': 0
            },
            'sample_results': {},
            'metadata_results': {},
            'analysis_results': {},
            'sample_reports': {},
            'metadata_reports': {},
            'analysis_reports': {}
        }

        has_samples = any(k in self.supported_sample_types for k in data.keys())
        has_analyses = any(k in self.supported_analysis_types for k in data.keys())

        if has_samples:
            print("Sample types in data:", [k for k in data.keys() if k in self.supported_sample_types])
            for sample_type, samples in data.items():
                if sample_type in self.supported_sample_types:
                    if not samples:
                        print(f"No samples found for type '{sample_type}'. Skipping.")
                        continue

                    print(f"Validating {len(samples)} {sample_type} samples...")

                    validator = self.sample_validators[sample_type]

                    validation_kwargs = {
                        'validate_relationships': validate_relationships,
                        'all_samples': data
                    }

                    if sample_type in ['organoid', 'specimen_from_organism']:
                        validation_kwargs['validate_ontology_text'] = validate_ontology_text

                    results = validator.validate_records(samples, **validation_kwargs)

                    # Store results
                    all_results['sample_types_processed'].append(sample_type)
                    all_results['sample_results'][sample_type] = results

                    # Generate report
                    report = validator.generate_validation_report(results)
                    all_results['sample_reports'][sample_type] = report

                    # Update total summary
                    summary = results['summary']
                    all_results['total_summary']['total_samples'] += summary['total']
                    all_results['total_summary']['valid_samples'] += summary['valid']
                    all_results['total_summary']['invalid_samples'] += summary['invalid']
                    all_results['total_summary']['warnings'] += summary['warnings']
                    all_results['total_summary']['relationship_errors'] += summary['relationship_errors']

        # Process metadata types
        for metadata_type, metadata_records in data.items():
            # Check if this metadata type is supported for the current context
            if metadata_type in self.supported_metadata_types or metadata_type in self.supported_analysis_metadata_types:
                print(f"Validating {metadata_type} metadata...")

                if has_analyses and not has_samples and metadata_type in self.supported_analysis_metadata_types:
                    validator = self.analysis_metadata_validators[metadata_type]
                elif metadata_type in self.supported_metadata_types:
                    validator = self.metadata_validators[metadata_type]
                else:
                    continue

                results = validator.validate_records(metadata_records)

                # Store results
                all_results['metadata_types_processed'].append(metadata_type)
                all_results['metadata_results'][metadata_type] = results

                # Generate report
                report = validator.generate_validation_report(results)
                all_results['metadata_reports'][metadata_type] = report

                # Update metadata summary (only if no error)
                if 'error' not in results:
                    summary = results['summary']
                    all_results['metadata_summary']['total_metadata'] += summary['total']
                    all_results['metadata_summary']['valid_metadata'] += summary['valid']
                    all_results['metadata_summary']['invalid_metadata'] += summary['invalid']
                else:
                    # If there's an error (no data), still count it
                    all_results['metadata_summary']['invalid_metadata'] += 1

        # Process analysis types
        if has_analyses:
            print("Analysis types in data:", [k for k in data.keys() if k in self.supported_analysis_types])
            for analysis_type, analyses in data.items():
                if analysis_type in self.supported_analysis_types:
                    if not analyses:
                        print(f"No analyses found for type '{analysis_type}'. Skipping.")
                        continue

                    print(f"Validating {len(analyses)} {analysis_type} analyses...")

                    validator = self.analysis_validators[analysis_type]
                    results = validator.validate_records(analyses)

                    # Store results
                    all_results['analysis_types_processed'].append(analysis_type)
                    all_results['analysis_results'][analysis_type] = results

                    # Generate report
                    report = validator.generate_validation_report(results)
                    all_results['analysis_reports'][analysis_type] = report

                    # Update analysis summary
                    summary = results['summary']
                    all_results['analysis_summary']['total_analyses'] += summary['total']
                    all_results['analysis_summary']['valid_analyses'] += summary['valid']
                    all_results['analysis_summary']['invalid_analyses'] += summary['invalid']
                    all_results['analysis_summary']['warnings'] += summary['warnings']

        return all_results

    def generate_unified_report(self, validation_results: Dict[str, Any]) -> str:
        report_lines = []

        # Individual metadata reports
        if validation_results['metadata_types_processed']:
            for metadata_type in validation_results['metadata_types_processed']:
                report_lines.append(f"\n{validation_results['metadata_reports'][metadata_type]}")
                report_lines.append("\n" + "-" * 60)

        # Individual sample reports
        if validation_results['sample_types_processed']:
            for sample_type in validation_results['sample_types_processed']:
                report_lines.append(f"\n{validation_results['sample_reports'][sample_type]}")
                report_lines.append("\n" + "-" * 60)

        # Analysis reports
        if validation_results['analysis_types_processed']:
            for analysis_type in validation_results['analysis_types_processed']:
                report_lines.append(f"\n{validation_results['analysis_reports'][analysis_type]}")
                report_lines.append("\n" + "-" * 60)

        return "\n".join(report_lines)

    def export_valid_samples_to_biosample(self, validation_results: Dict[str, Any]) -> Dict[str, List[Dict]]:
        biosample_exports = {}

        for sample_type in validation_results['sample_types_processed']:
            results = validation_results['sample_results'][sample_type]
            valid_samples_key = f'valid_{sample_type}s'

            if valid_samples_key in results and results[valid_samples_key]:
                validator = self.sample_validators[sample_type]
                biosample_exports[sample_type] = []

                for valid_sample in results[valid_samples_key]:
                    biosample_data = validator.export_to_biosample_format(valid_sample['model'])
                    biosample_exports[sample_type].append({
                        'sample_name': valid_sample['sample_name'],
                        'biosample_format': biosample_data
                    })
        return biosample_exports

    def get_supported_types(self) -> Dict[str, List[str]]:
        return {
            'sample_types': list(self.supported_sample_types),
            'metadata_types': list(self.supported_metadata_types),
            'analysis_types': list(self.supported_analysis_types),
            'analysis_metadata_types': list(self.supported_analysis_metadata_types)
        }