import json
import time
from unified_validator import UnifiedFAANGValidator


def main():
    file_path = 'json_files/sample1.json'

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            faang_json_data = json.load(f)

        validator = UnifiedFAANGValidator()

        print("FAANG Sample Validation")
        print("=" * 50)
        supported = validator.get_supported_types()
        print(f"Supported sample types: {', '.join(supported['sample_types'])}")
        print(f"Supported metadata types: {', '.join(supported['metadata_types'])}")
        print()

        # prefetch ontology terms
        print("=" * 50)
        print("STEP 1: Pre-fetching ontology terms...")
        print("=" * 50)

        validator.prefetch_all_ontology_terms(faang_json_data)
        print()

        # pre-fetch BioSample IDs
        print("=" * 50)
        print("STEP 2: Pre-fetching BioSample IDs...")
        print("=" * 50)

        validator.prefetch_all_biosample_ids(faang_json_data)
        print()

        # run validation
        print("=" * 50)
        print("STEP 3: Running validation...")
        print("=" * 50)

        results = validator.validate_all_records(
            faang_json_data,
            validate_relationships=True,
            validate_ontology_text=True
        )
        print()

        report = validator.generate_unified_report(results)
        print(report)

        # BioSample format
        biosample_exports = validator.export_valid_samples_to_biosample(results)

        # Optional: Print metadata validation details
        # print("\n" + "=" * 60)
        # print("METADATA VALIDATION STATUS")
        # print("=" * 60)
        #
        # for metadata_type in results['metadata_types_processed']:
        #     metadata_result = results['metadata_results'][metadata_type]
        #     if 'error' in metadata_result:
        #         print(f"\n{metadata_type.upper()}: ERROR")
        #         print(f"  {metadata_result['error']}")
        #     else:
        #         print(f"\n{metadata_type.upper()}:")
        #         print(f"  Total: {metadata_result['summary']['total']}")
        #         print(f"  Valid: {metadata_result['summary']['valid']}")
        #         print(f"  Invalid: {metadata_result['summary']['invalid']}")
        #
        #         # Show valid metadata details
        #         if metadata_result['valid']:
        #             print(f"  Valid {metadata_type} records:")
        #             for item in metadata_result['valid']:
        #                 print(f"    - Index {item['index']}: {item['data']}")

        # save results to file
        save_results = True
        if save_results:
            output_file = "validation_results.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'validation_results': results,
                    'biosample_exports': biosample_exports
                }, f, indent=2, default=str)
            print(f"\nResults saved to: {output_file}")

    except FileNotFoundError:
        raise FileNotFoundError(f"Sample file not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in file {file_path}: {e}")
    except Exception as e:
        print(f"Error during validation: {e}")
        raise


if __name__ == "__main__":
    main()