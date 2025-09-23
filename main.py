import json
from unified_validator import UnifiedFAANGValidator


def main():
    """Main function to run FAANG sample validation"""

    # Sample JSON data (you can replace this with file reading)
    sample_json_data = {
        "organism": [
            {
                "Sample Name": "ECA_UKY_H11",
                "Sample Description": "Foal",
                "Material": "organism",
                "Term Source ID": "OBI_0100026",
                "Project": "FAANG",
                "Secondary Project": "AQUA-FAANG",
                "Availability": "",
                "Same as": "",
                "Organism": "Equus caballus",
                "Organism Term Source ID": "NCBITaxon:9796",
                "Sex": "male",
                "Sex Term Source ID": "PATO_0000384",
                "Birth Date": "2013-02",
                "Unit": "YYYY-MM",
                "Health Status": [
                    {
                        "text": "normal",
                        "term": "PATO:0000461"
                    }
                ],
                "Diet": "",
                "Birth Location": "",
                "Birth Location Latitude": "",
                "Birth Location Latitude Unit": "",
                "Birth Location Longitude": "",
                "Birth Location Longitude Unit": "",
                "Birth Weight": "",
                "Birth Weight Unit": "",
                "Placental Weight": "",
                "Placental Weight Unit": "",
                "Pregnancy Length": "",
                "Pregnancy Length Unit": "",
                "Delivery Timing": "",
                "Delivery Ease": "",
                "Child Of": ["", ""],
                "Pedigree": ""
            },
            {
                "Sample Name": "ECA_UKY_H1",
                "Sample Description": "Foal, 9 days old, Thoroughbred",
                "Material": "organism",
                "Term Source ID": "OBI_0100026",
                "Project": "FAANG",
                "Secondary Project": "AQUA-FAANG",
                "Availability": "",
                "Same as": "",
                "Organism": "Equus caballus",
                "Organism Term Source ID": "NCBITaxon:9796",
                "Sex": "female",
                "Sex Term Source ID": "PATO_0000383",
                "Birth Date": "2014-07",
                "Unit": "YYYY-MM",
                "Health Status": [
                    {
                        "text": "normal",
                        "term": "PATO:0000461"
                    }
                ],
                "Diet": "",
                "Birth Location": "",
                "Birth Location Latitude": "",
                "Birth Location Latitude Unit": "",
                "Birth Location Longitude": "",
                "Birth Location Longitude Unit": "",
                "Birth Weight": "",
                "Birth Weight Unit": "",
                "Placental Weight": "",
                "Placental Weight Unit": "",
                "Pregnancy Length": "",
                "Pregnancy Length Unit": "",
                "Delivery Timing": "",
                "Delivery Ease": "",
                "Child Of": ["ECA_UKY_H11", ""],
                "Pedigree": ""
            }
        ],
        "organoid": [
            {
                "Sample Name": "OCU_INRAE_S1",
                "Sample Description": "Rabbit caecum organoid cell monolayer, cell culture insert 1 (immerged condition)",
                "Material": "organoid",
                "Term Source ID": "NCIT_C172259",
                "Project": "FAANG",
                "Secondary Project": "",
                "Availability": "",
                "Same as": "",
                "Organ Model": "Caecum",
                "Organ Model Term Source ID": "UBERON:0001153",
                "Organ Part Model": "Caecum epithelium",
                "Organ Part Model Term Source ID": "UBERON:0005636",
                "Freezing Date": "restricted access",
                "Unit": "restricted access",
                "Freezing Method": "fresh",
                "Freezing Protocol": "restricted access",
                "Number Of Frozen Cells": "",
                "Number Of Frozen Cells Unit": "",
                "Organoid Culture And Passage Protocol": "https://api.faang.org/files/protocols/samples/INRAE_SOP_METABOWEAN_20250206.pdf",
                "Organoid Passage": "2",
                "Organoid Passage Unit": "passages",
                "Organoid Passage Protocol": "https://api.faang.org/files/protocols/samples/INRAE_SOP_METABOWEAN_20250206.pdf",
                "Type Of Organoid Culture": "2D",
                "Organoid Morphology": "",
                "Growth Environment": "matrigel",
                "Growth Environment Unit": "1",
                "Stored Oxygen Level": "",
                "Stored Oxygen Level Unit": "",
                "Incubation Temperature": "",
                "Incubation Temperature Unit": "",
                "Derived From": "OCU_INRAE_PND18_S1"
            },
            {
                "Sample Name": "OCU_INRAE_S2",
                "Sample Description": "Rabbit caecum organoid cell monolayer, cell culture insert 2 (immerged condition)",
                "Material": "organoid",
                "Term Source ID": "NCIT_C172259",
                "Project": "FAANG",
                "Secondary Project": "",
                "Availability": "",
                "Same as": "",
                "Organ Model": "Caecum",
                "Organ Model Term Source ID": "UBERON:0001153",
                "Organ Part Model": "Caecum epithelium",
                "Organ Part Model Term Source ID": "UBERON:0005636",
                "Freezing Date": "restricted access",
                "Unit": "restricted access",
                "Freezing Method": "fresh",
                "Freezing Protocol": "restricted access",
                "Number Of Frozen Cells": "",
                "Number Of Frozen Cells Unit": "",
                "Organoid Culture And Passage Protocol": "https://api.faang.org/files/protocols/samples/INRAE_SOP_METABOWEAN_20250206.pdf",
                "Organoid Passage": "2",
                "Organoid Passage Unit": "passages",
                "Organoid Passage Protocol": "https://api.faang.org/files/protocols/samples/INRAE_SOP_METABOWEAN_20250206.pdf",
                "Type Of Organoid Culture": "2D",
                "Organoid Morphology": "",
                "Growth Environment": "matrigel",
                "Growth Environment Unit": "1",
                "Stored Oxygen Level": "",
                "Stored Oxygen Level Unit": "",
                "Incubation Temperature": "",
                "Incubation Temperature Unit": "",
                "Derived From": "OCU_INRAE_PND18_S19"
            }
        ],
        "specimen_from_organism": [
            {
                "Health Status": [
                    {
                        "text": "normal",
                        "term": "PATO:0000461"
                    }
                ],
                "Sample Name": "OCU_INRAE_PND18_S1",
                "Sample Description": "Adipose Tissue, H1",
                "Material": "specimen from organism",
                "Term Source ID": "OBI_0001479",
                "Project": "FAANG",
                "Secondary Project": "",
                "Availability": "",
                "Same as": "",
                "Specimen Collection Date": "2005-05",
                "Unit": "YYYY-MM",
                "Geographic Location": "Denmark",
                "Animal Age At Collection": "23.5",
                "Animal Age At Collection Unit": "month",
                "Developmental Stage": "adult",
                "Developmental Stage Term Source ID": "EFO_0001272",
                "Organism Part": "adipose tissue",
                "Organism Part Term Source ID": "UBERON_0001013",
                "Specimen Collection Protocol": "ftp://ftp.faang.ebi.ac.uk/ftp/protocols/samples/WUR_SOP_animal_sampling_20160405.pdf",
                "Fasted Status": "",
                "Number of Pieces": "",
                "Number of Pieces Unit": "",
                "Specimen Volume": "",
                "Specimen Volume Unit": "",
                "Specimen Size": "",
                "Specimen Size Unit": "",
                "Specimen Weight": "",
                "Specimen Weight Unit": "",
                "Specimen Picture URL": "",
                "Gestational Age At Sample Collection": "",
                "Gestational Age At Sample Collection Unit": "",
                "Average Incubation temperature": "",
                "Average Incubation temperature Unit": "",
                "Average Incubation Humidity": "",
                "Average Incubation Humidity Unit": "",
                "Embryonic Stage": "",
                "Embryonic Stage Unit": "",
                "Derived From": "OCU_INRAE_PND18"
            }
        ]
    }

    try:
        # Create the unified validator
        validator = UnifiedFAANGValidator()

        print("FAANG Sample Validation System")
        print("=" * 50)
        print(f"Supported sample types: {', '.join(validator.get_supported_types())}")
        print()

        # Run validation
        results = validator.validate_all_samples(
            sample_json_data,
            validate_relationships=True,
            validate_ontology_text=True
        )

        # Generate and print the unified report
        report = validator.generate_unified_report(results)
        print(report)

        # Get validation summary
        summary = validator.get_validation_summary(results)
        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)
        print(json.dumps(summary, indent=2))

        # Export valid samples to BioSample format
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

        # Save results to file (optional)
        save_results = True  # Set to False if you don't want to save
        if save_results:
            output_file = "validation_results.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'validation_results': results,
                    'biosample_exports': biosample_exports
                }, f, indent=2, default=str)
            print(f"\nResults saved to: {output_file}")

    except Exception as e:
        print(f"Error during validation: {e}")
        raise


def validate_from_file(file_path: str):
    """Alternative function to validate samples from a JSON file"""
    try:
        validator = UnifiedFAANGValidator()
        results = validator.validate_sample_file(
            file_path,
            validate_relationships=True,
            validate_ontology_text=True
        )

        # Generate report
        report = validator.generate_unified_report(results)
        print(report)

        return results

    except Exception as e:
        print(f"Error validating file {file_path}: {e}")
        raise


if __name__ == "__main__":
    # Run validation with embedded sample data
    main()

    # Uncomment the line below to validate from a file instead
    # validate_from_file('json_files/sample1.json')