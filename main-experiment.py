import json
from datetime import datetime
from validation.unified_validator import UnifiedFAANGValidator
from validation.generic_validator_classes import collect_ontology_terms_from_experiments

# Import ExperimentSubmitter from your submission module
# Adjust the import path based on your project structure
try:
    from submission.experiment.experiment_submitter import ExperimentSubmitter
except ImportError:
    print("Warning: ExperimentSubmitter not found. Submission will be disabled.")
    ExperimentSubmitter = None


def normalize_experiment_ena_record(record: dict) -> dict:
    normalized = {}
    for key, value in record.items():
        if isinstance(value, list):
            if len(value) >= 1:
                normalized[key] = value[0]
            else:
                normalized[key] = ""
        else:
            normalized[key] = value
    return normalized


def normalize_run_record(record: dict) -> dict:
    # Field name mappings: JSON name -> Expected name
    field_mappings = {
        'Run center': 'Run Center',
        'Run date': 'Run Date',
        'Experiment Ref': 'Experiment Ref',
        'Checksum Method': 'Checksum Method',
        'Filename pair': 'Filename Pair',
        'Filetype pair': 'Filetype Pair',
        'Checksum method pair': 'Checksum Method Pair',
        'Checksum pair': 'Checksum Pair'
    }

    normalized = {}
    for key, value in record.items():
        normalized_key = field_mappings.get(key, key)
        normalized[normalized_key] = value

    return normalized


def main():
    file_path = 'json_files/experiment/small_exp.json'

    # =====================================================================
    # CONFIGURATION
    # =====================================================================
    ENABLE_SUBMISSION = True  # Set to True to enable ENA submission
    SUBMISSION_MODE = 'test'  # 'test' or 'prod'
    SUBMISSION_ACTION = 'submission'  # 'submission' or 'update'

    # Credentials (only needed if ENABLE_SUBMISSION = True)
    WEBIN_USERNAME = 'your_username'
    WEBIN_PASSWORD = 'your_password'
    # =====================================================================

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            faang_json_data = json.load(f)

        validator = UnifiedFAANGValidator()

        print("FAANG Experiment Validation & Submission")
        print("=" * 60)
        supported = validator.get_supported_types()
        print(f"Supported experiment types: {', '.join(supported['experiment_types'])}")
        print()

        # STEP 1: Pre-fetch ontology terms
        print("=" * 60)
        print("STEP 1: Pre-fetching ontology terms...")
        print("=" * 60)

        experiment_terms = collect_ontology_terms_from_experiments(faang_json_data)

        if experiment_terms:
            print(f"Found {len(experiment_terms)} unique ontology terms to fetch")
            validator.shared_ontology_validator.batch_fetch_from_ols_sync(list(experiment_terms))
            print(f"✓ Ontology terms cached in shared validator")
        else:
            print("No ontology terms found in experiment data")
        print()

        # STEP 2: Run validation
        print("=" * 60)
        print("STEP 2: Running experiment validation...")
        print("=" * 60)

        results = validator.validate_all_records(
            faang_json_data,
            validate_relationships=True,
            validate_ontology_text=True
        )
        print()

        # Generate and print report
        report = validator.generate_unified_report(results)
        print(report)

        # Check if validation was successful
        if results['experiment_summary']['invalid_experiments'] > 0:
            print("\n⚠ Validation failed. Cannot proceed with submission.")
            return

        print("\n✓ All experiments validated successfully")

        # STEP 3: Submit to ENA (if enabled)
        print("\n" + "=" * 60)
        print("STEP 3: ENA Submission")
        print("=" * 60)

        if not ENABLE_SUBMISSION:
            print("⚠ Submission is DISABLED for testing")
            print()
            print("Validated data is ready for submission.")
            print("You can now compare validation results or enable submission.")
            return

        # Check if ExperimentSubmitter is available
        if ExperimentSubmitter is None:
            print("✗ ExperimentSubmitter not available. Cannot submit.")
            print("  Make sure the submission module is properly installed.")
            return

        # Submit to ENA
        print(f"Submitting to ENA (mode: {SUBMISSION_MODE}, action: {SUBMISSION_ACTION})...")

        # Add ENA-specific sheets from original JSON to results
        if 'experiment ena' in faang_json_data:
            if 'experiment ena' not in results['experiment_results']:
                results['experiment_results']['experiment ena'] = {'valid': [], 'invalid': []}
            for record in faang_json_data['experiment ena']:
                normalized_record = normalize_experiment_ena_record(record)
                results['experiment_results']['experiment ena']['valid'].append({
                    'model': normalized_record,
                    'data': normalized_record
                })

        if 'run' in faang_json_data:
            if 'run' not in results['metadata_results']:
                results['metadata_results']['run'] = {'valid': [], 'invalid': []}
            for record in faang_json_data['run']:
                normalized_record = normalize_run_record(record)
                results['metadata_results']['run']['valid'].append({
                    'model': normalized_record,
                    'data': normalized_record
                })

        if 'study' in faang_json_data:
            if 'study' not in results['metadata_results']:
                results['metadata_results']['study'] = {'valid': [], 'invalid': []}
            for record in faang_json_data['study']:
                results['metadata_results']['study']['valid'].append({
                    'model': record,
                    'data': record
                })

        if 'submission' in faang_json_data:
            if 'submission' not in results['metadata_results']:
                results['metadata_results']['submission'] = {'valid': [], 'invalid': []}
            for record in faang_json_data['submission']:
                results['metadata_results']['submission']['valid'].append({
                    'model': record,
                    'data': record
                })

        credentials = {
            'username': WEBIN_USERNAME,
            'password': WEBIN_PASSWORD,
            'mode': SUBMISSION_MODE
        }

        submitter = ExperimentSubmitter()

        result = submitter.submit_to_ena(
            results=results,
            credentials=credentials,
            action=SUBMISSION_ACTION
        )

        # Check if result is None (shouldn't happen but handle it)
        if result is None:
            print()
            print("=" * 60)
            print("SUBMISSION RESULTS")
            print("=" * 60)
            print("✗ Submission returned None - this indicates an unexpected error")
            print("  Check the console output above for error details")
            return

        # Print results
        print()
        print("=" * 60)
        print("SUBMISSION RESULTS")
        print("=" * 60)

        if result.get('success'):
            print(f"✓ {result.get('message', 'Submission successful')}")

            if result.get('submission_results'):
                print(f"\nSubmission Details:")
                print(result['submission_results'])

            if result.get('info_messages'):
                print(f"\nInfo Messages:")
                for msg in result['info_messages']:
                    print(f"  • {msg}")
        else:
            print(f"✗ {result.get('message', 'Submission failed')}")

            if result.get('errors'):
                print(f"\nErrors:")
                for error in result['errors']:
                    print(f"  • {error}")

        print()

    except FileNotFoundError:
        raise FileNotFoundError(f"Experiment file not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in file {file_path}: {e}")
    except Exception as e:
        print(f"Error during validation/submission: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()