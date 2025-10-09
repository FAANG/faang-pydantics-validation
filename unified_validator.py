from typing import Dict, List, Any
from teleostei_embryo_validator import TeleosteiEmbryoValidator
from organism_validator import OrganismValidator
from organoid_validator import OrganoidValidator
from specimen_validator import SpecimenValidator
from teleostei_post_hatching_validator import TeleosteiPostHatchingValidator
from single_cell_specimen_validator import SingleCellSpecimenValidator
from generic_validator_classes import collect_ontology_terms_from_data


class UnifiedFAANGValidator:
    def __init__(self):
        self.validators = {
            'organism': OrganismValidator(),
            'organoid': OrganoidValidator(),
            'specimen_from_organism': SpecimenValidator(),
            'teleostei_embryo': TeleosteiEmbryoValidator(),
            'teleostei_post_hatching': TeleosteiPostHatchingValidator(),
            'single_cell_specimen': SingleCellSpecimenValidator()
            # 'cell_culture': CellCultureValidator(),
            # 'cell_line': CellLineValidator(),
        }
        self.supported_sample_types = set(self.validators.keys())

    def prefetch_all_ontology_terms(self, data: Dict[str, List[Dict[str, Any]]]):
        # collect unique term IDs
        term_ids = collect_ontology_terms_from_data(data)

        if not term_ids:
            print("No ontology terms to pre-fetch")
            return


        # use the first validator's ontology_validator to fetch all terms since all validators share the same cache
        # we only fetch once
        for validator in self.validators.values():
            if validator.ontology_validator:
                validator.ontology_validator.batch_fetch_from_ols_sync(list(term_ids))
                print(f"Pre-fetch complete. Cache now contains {len(validator.ontology_validator._cache)} terms.")

                # share cache with all other validators to avoid redundant fetching
                for other_validator in self.validators.values():
                    if other_validator.ontology_validator and other_validator.ontology_validator != validator.ontology_validator:
                        other_validator.ontology_validator._cache = validator.ontology_validator._cache

                break

    def validate_all_records(
        self,
        data: Dict[str, List[Dict[str, Any]]],
        validate_relationships: bool = True,
        validate_ontology_text: bool = True
    ) -> Dict[str, Any]:

        all_results = {
            'sample_types_processed': [],
            'total_summary': {
                'total_samples': 0,
                'valid_samples': 0,
                'invalid_samples': 0,
                'warnings': 0,
                'relationship_errors': 0
            },
            'results_by_type': {},
            'reports_by_type': {}
        }

        # process each record type
        print("Sample types in data:", list(data.keys()))
        for sample_type, samples in data.items():
            if sample_type not in self.supported_sample_types:
                print(f"Warning: Sample type '{sample_type}' is not supported. Skipping.")
                continue

            if not samples:
                print(f"No samples found for type '{sample_type}'. Skipping.")
                continue

            print(f"Validating {len(samples)} {sample_type} samples...")

            validator = self.validators[sample_type]

            # Validate samples with appropriate parameters
            validation_kwargs = {
                'validate_relationships': validate_relationships,
                'all_samples': data
            }

            # Add specific parameters for sample types that support ontology text validation
            if sample_type in ['organoid', 'specimen_from_organism']:
                validation_kwargs['validate_ontology_text'] = validate_ontology_text

            results = validator.validate_records(samples, **validation_kwargs)

            # Store results
            all_results['sample_types_processed'].append(sample_type)
            all_results['results_by_type'][sample_type] = results

            # Generate report
            report = validator.generate_validation_report(results)
            all_results['reports_by_type'][sample_type] = report

            # Update total summary
            summary = results['summary']
            all_results['total_summary']['total_samples'] += summary['total']
            all_results['total_summary']['valid_samples'] += summary['valid']
            all_results['total_summary']['invalid_samples'] += summary['invalid']
            all_results['total_summary']['warnings'] += summary['warnings']
            all_results['total_summary']['relationship_errors'] += summary['relationship_errors']

        return all_results

    def generate_unified_report(self, validation_results: Dict[str, Any]) -> str:
        report_lines = []

        # Individual reports by type
        for sample_type in validation_results['sample_types_processed']:
            report_lines.append(f"\n{validation_results['reports_by_type'][sample_type]}")
            report_lines.append("\n" + "-" * 60)

        return "\n".join(report_lines)

    def export_valid_samples_to_biosample(self, validation_results: Dict[str, Any]) -> Dict[str, List[Dict]]:
        biosample_exports = {}

        for sample_type in validation_results['sample_types_processed']:
            results = validation_results['results_by_type'][sample_type]
            valid_samples_key = f'valid_{sample_type}s'

            if valid_samples_key in results and results[valid_samples_key]:
                validator = self.validators[sample_type]
                biosample_exports[sample_type] = []

                for valid_sample in results[valid_samples_key]:
                    biosample_data = validator.export_to_biosample_format(valid_sample['model'])
                    biosample_exports[sample_type].append({
                        'sample_name': valid_sample['sample_name'],
                        'biosample_format': biosample_data
                    })
        return biosample_exports

    def get_supported_types(self) -> List[str]:
        return list(self.supported_sample_types)