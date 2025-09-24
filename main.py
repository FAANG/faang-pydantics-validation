import asyncio
import json
import time
from unified_validator import UnifiedFAANGValidator


async def main():

    file_path = 'json_files/sample1.json'
    start_time = time.time()

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
        validation_start = time.time()
        results = await validator.validate_all_samples(
            sample_json_data,
            validate_relationships=True,
            validate_ontology_text=True
        )
        validation_end = time.time()

        print(f"Validation completed in {validation_end - validation_start:.2f} seconds")
        print()

        # Generate and print the unified report
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
        save_results = True
        if save_results:
            output_file = "validation_results.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'validation_results': results,
                    'biosample_exports': biosample_exports
                }, f, indent=2, default=str)
            print(f"\nResults saved to: {output_file}")

        # Performance summary
        total_time = time.time() - start_time
        print(f"\nTotal execution time: {total_time:.2f} seconds")
        print(f"Async validation time: {validation_end - validation_start:.2f} seconds")

    except FileNotFoundError:
        print(f"Error: Sample file not found: {file_path}")
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in file {file_path}: {e}")
    except Exception as e:
        print(f"Error during validation: {e}")
        raise


async def validate_from_file_async(file_path: str):
    """Alternative async function to validate samples from a JSON file"""
    try:
        validator = UnifiedFAANGValidator()

        start_time = time.time()
        results = await validator.validate_sample_file(
            file_path,
            validate_relationships=True,
            validate_ontology_text=True
        )
        end_time = time.time()

        # Generate report
        report = validator.generate_unified_report(results)
        print(report)

        print(f"\nAsync validation completed in {end_time - start_time:.2f} seconds")

        return results

    except Exception as e:
        print(f"Error validating file {file_path}: {e}")
        raise


if __name__ == "__main__":
    # Run async validation
    asyncio.run(main())

    # Alternative: Validate from file
    # asyncio.run(validate_from_file_async('json_files/sample1.json'))