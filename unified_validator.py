import asyncio
from typing import Dict, List, Any, Optional
import json
from organism_validator import OrganismValidator
from organoid_validator import OrganoidValidator


class UnifiedFAANGValidator:
    def __init__(self):
        self.validators = {
            'organism': OrganismValidator(),
            'organoid': OrganoidValidator(),
            # Add more sample types here as needed
        }
        self.supported_sample_types = set(self.validators.keys())

    async def validate_all_samples(
        self,
        data: Dict[str, List[Dict[str, Any]]],
        validate_relationships: bool = True,
        validate_ontology_text: bool = True
    ) -> Dict[str, Any]:
        """
        Async validate all sample types with concurrent processing
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

        # Create tasks for concurrent processing of different sample types
        validation_tasks = []
        sample_types_to_process = []

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

            # Add specific parameters for different sample types
            if sample_type == 'organoid':
                validation_kwargs['validate_ontology_text'] = validate_ontology_text

            # Create async task for this sample type
            task = validator.validate_samples(samples, **validation_kwargs)
            validation_tasks.append((sample_type, task))
            sample_types_to_process.append(sample_type)

        # Run all sample type validations concurrently
        if validation_tasks:
            print("Running validation for all sample types concurrently...")

            # Execute all validation tasks concurrently
            task_results = await asyncio.gather(
                *[task for _, task in validation_tasks],
                return_exceptions=True
            )

            # Process results
            for (sample_type, _), result in zip(validation_tasks, task_results):
                if isinstance(result, Exception):
                    print(f"Error validating {sample_type}: {result}")
                    continue

                # Store results
                all_results['sample_types_processed'].append(sample_type)
                all_results['results_by_type'][sample_type] = result

                # Generate report (synchronous operation)
                validator = self.validators[sample_type]
                report = validator.generate_validation_report(result)
                all_results['reports_by_type'][sample_type] = report

                # Update total summary
                summary = result['summary']
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

    async def validate_sample_file(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """Async validate samples from a JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return await self.validate_all_samples(data, **kwargs)

        except FileNotFoundError:
            raise FileNotFoundError(f"Sample file not found: {file_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in file {file_path}: {e}")
        except Exception as e:
            raise Exception(f"Error validating file {file_path}: {e}")

    def add_validator(self, sample_type: str, validator_instance):
        """Add a new validator for a sample type"""
        self.validators[sample_type] = validator_instance
        self.supported_sample_types.add(sample_type)

    def get_supported_types(self) -> List[str]:
        """Get list of supported sample types"""
        return list(self.supported_sample_types)