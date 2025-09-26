from typing import Dict, List, Any, Optional
import json
from organism_validator import OrganismValidator
from organoid_validator import OrganoidValidator
from specimen_validator import SpecimenValidator


class UnifiedFAANGValidator:
    def __init__(self):
        self.validators = {
            'organism': OrganismValidator(),
            'organoid': OrganoidValidator(),
            'specimen_from_organism': SpecimenValidator(),
            # Add more sample types here as needed
            # 'cell_culture': CellCultureValidator(),
            # 'cell_line': CellLineValidator(),
        }
        self.supported_sample_types = set(self.validators.keys())

    def validate_all_samples(
        self,
        data: Dict[str, List[Dict[str, Any]]],
        validate_relationships: bool = True,
        validate_ontology_text: bool = True
    ) -> Dict[str, Any]:
        """
        Validate all sample types in the provided data

        Args:
            data: Dictionary with sample type keys and lists of samples
            validate_relationships: Whether to validate cross-sample relationships
            validate_ontology_text: Whether to validate ontology text consistency

        Returns:
            Dictionary containing validation results for all sample types
        """
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

        # Process each sample type
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

            results = validator.validate_samples(samples, **validation_kwargs)

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
        """Generate a unified validation report for all sample types"""
        report_lines = []

        # Header
        report_lines.append("=" * 60)
        report_lines.append("FAANG UNIFIED VALIDATION REPORT")
        report_lines.append("=" * 60)

        # Overall summary
        summary = validation_results['total_summary']
        report_lines.append(f"\nOVERALL SUMMARY:")
        report_lines.append(f"Sample types processed: {', '.join(validation_results['sample_types_processed'])}")
        report_lines.append(f"Total samples: {summary['total_samples']}")
        report_lines.append(f"Valid samples: {summary['valid_samples']}")
        report_lines.append(f"Invalid samples: {summary['invalid_samples']}")
        report_lines.append(f"Samples with warnings: {summary['warnings']}")
        report_lines.append(f"Samples with relationship errors: {summary['relationship_errors']}")

        # Success rate
        if summary['total_samples'] > 0:
            success_rate = (summary['valid_samples'] / summary['total_samples']) * 100
            report_lines.append(f"Success rate: {success_rate:.1f}%")

        report_lines.append("\n" + "=" * 60)

        # Individual reports by type
        for sample_type in validation_results['sample_types_processed']:
            report_lines.append(f"\n{validation_results['reports_by_type'][sample_type]}")
            report_lines.append("\n" + "-" * 60)

        return "\n".join(report_lines)

    def export_valid_samples_to_biosample(self, validation_results: Dict[str, Any]) -> Dict[str, List[Dict]]:
        """Export all valid samples to BioSample format"""
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

    def get_validation_summary(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Get a concise validation summary"""
        summary_by_type = {}

        for sample_type in validation_results['sample_types_processed']:
            results = validation_results['results_by_type'][sample_type]
            summary = results['summary']

            summary_by_type[sample_type] = {
                'total': summary['total'],
                'valid': summary['valid'],
                'invalid': summary['invalid'],
                'success_rate': f"{(summary['valid'] / summary['total'] * 100):.1f}%" if summary['total'] > 0 else "0%",
                'has_warnings': summary['warnings'] > 0,
                'has_relationship_errors': summary['relationship_errors'] > 0
            }

        return {
            'overall': validation_results['total_summary'],
            'by_type': summary_by_type
        }

    def add_validator(self, sample_type: str, validator_instance):
        """Add a new validator for a sample type"""
        self.validators[sample_type] = validator_instance
        self.supported_sample_types.add(sample_type)

    def get_supported_types(self) -> List[str]:
        """Get list of supported sample types"""
        return list(self.supported_sample_types)

    def configure_validation(self, **config_options):
        """Configure validation options for all validators"""
        for validator in self.validators.values():
            if hasattr(validator, 'config'):
                for key, value in config_options.items():
                    if hasattr(validator.config, key):
                        setattr(validator.config, key, value)

    def get_validation_config_summary(self) -> Dict[str, Any]:
        """Get summary of current validation configuration"""
        config_summary = {}

        for sample_type, validator in self.validators.items():
            if hasattr(validator, 'config'):
                config_summary[sample_type] = {
                    'external_biosample_validation': getattr(validator.config, 'enable_external_biosample_validation',
                                                             False),
                    'relationship_chain_validation': getattr(validator.config, 'enable_relationship_chain_validation',
                                                             False),
                    'circular_reference_detection': getattr(validator.config, 'enable_circular_reference_detection',
                                                            False),
                    'ols_text_validation': getattr(validator.config, 'enable_ols_text_validation', False),
                    'max_relationship_depth': getattr(validator.config, 'max_relationship_depth', 10),
                }
            else:
                config_summary[sample_type] = {'basic_validation_only': True}

        return config_summary