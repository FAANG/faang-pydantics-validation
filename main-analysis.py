import json
from validation.unified_validator import UnifiedFAANGValidator


def main():
    file_path = 'json_files/analysis/analysis_complete.json'

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            faang_json_data = json.load(f)

        validator = UnifiedFAANGValidator()

        print("FAANG Analysis Validation")
        print("=" * 60)
        supported = validator.get_supported_types()
        print(f"Supported analysis types: {', '.join(supported['analysis_types'])}")
        print()

        # Note: Analyses typically don't have ontology terms or BioSample relationships
        # so we skip those prefetch steps

        # Run validation for analyses
        print("=" * 60)
        print("Running Analysis Validation...")
        print("=" * 60)

        results = validator.validate_all_records(
            faang_json_data,
            validate_relationships=False,  # Analyses don't have child_of/derived_from
            validate_ontology_text=False  # Analyses don't have ontology terms typically
        )
        print()

        # Generate and print report
        report = validator.generate_unified_report(results)
        print(report)

        # Save results to file
        save_results = True
        if save_results:
            output_file = "analysis_validation_results.json"

            # Create a clean output structure
            output_data = {
                'validation_summary': results['total_summary'],
                'analysis_types_processed': results['analysis_types_processed'],
                'analysis_results': {}
            }

            # Add detailed results for each analysis type
            for analysis_type in results['analysis_types_processed']:
                analysis_result = results['analysis_results'][analysis_type]
                output_data['analysis_results'][analysis_type] = {
                    'summary': analysis_result['summary'],
                    'valid_records': [
                        {
                            'index': r['index'],
                            'alias': r['data'].get('Alias'),
                            'warnings': r['warnings']
                        }
                        for r in analysis_result['valid']
                    ],
                    'invalid_records': [
                        {
                            'index': r['index'],
                            'alias': r['data'].get('Alias'),
                            'errors': r['errors']
                        }
                        for r in analysis_result['invalid']
                    ]
                }

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, default=str)
            print(f"Results saved to: {output_file}")

    except FileNotFoundError:
        raise FileNotFoundError(f"Analysis file not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in file {file_path}: {e}")
    except Exception as e:
        print(f"Error during validation: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()