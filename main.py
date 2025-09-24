import json
from unified_validator import UnifiedFAANGValidator


def main():
    file_path = 'json_files/sample1.json'

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            sample_json_data = json.load(f)

        # Create the unified validator
        validator = UnifiedFAANGValidator()

        print("FAANG Sample Validation")
        print("=" * 50)
        print(f"Supported sample types: {', '.join(validator.get_supported_types())}")
        print()

        # Run validation
        results = validator.validate_all_samples(
            sample_json_data,
            validate_relationships=True,
            validate_ontology_text=True
        )

        report = validator.generate_unified_report(results)
        print(report)

        # validation summary
        summary = validator.get_validation_summary(results)
        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)
        print(json.dumps(summary, indent=2))

        # BioSample format
        biosample_exports = validator.export_valid_samples_to_biosample(results)

        if biosample_exports:
            print("\n" + "=" * 60)
            print("BIOSAMPLE EXPORTS")
            print("=" * 60)

            for sample_type, exports in biosample_exports.items():
                print(f"\n{sample_type.upper()} SAMPLES:")
                print("-" * 30)

                for export in exports:
                    print(f"\nSample: {export['sample_name']}")
                    print(json.dumps(export['biosample_format'], indent=2))

        # save results to file (optional)
        save_results = True  # Set to False if you don't want to save
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
    # Run validation with embedded sample data
    main()