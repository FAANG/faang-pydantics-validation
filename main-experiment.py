import json
from validation.unified_validator import UnifiedFAANGValidator
from validation.generic_validator_classes import collect_ontology_terms_from_experiments


def main():
    file_path = 'json_files/experiment/small_exp.json'

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            faang_json_data = json.load(f)

        validator = UnifiedFAANGValidator()

        print("FAANG Experiment Validation")
        print("=" * 60)
        supported = validator.get_supported_types()
        print(f"Supported experiment types: {', '.join(supported['experiment_types'])}")
        print()

        # STEP 1: Pre-fetch ontology terms (experiments have ontology terms)
        print("=" * 60)
        print("STEP 1: Pre-fetching ontology terms...")
        print("=" * 60)

        # Collect ontology terms from experiments
        experiment_terms = collect_ontology_terms_from_experiments(faang_json_data)

        if experiment_terms:
            print(f"Found {len(experiment_terms)} unique ontology terms to fetch")
            # Pre-fetch using the shared ontology validator
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
            validate_relationships=True,  # Experiments have relationships (ChIP-seq controls)
            validate_ontology_text=True  # Optional: set to True if you want to validate ontology text matches
        )
        print()

        # Generate and print report
        report = validator.generate_unified_report(results)
        print(report)


    except FileNotFoundError:
        raise FileNotFoundError(f"Experiment file not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in file {file_path}: {e}")
    except Exception as e:
        print(f"Error during validation: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()