from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from pydantic import BaseModel
from typing import Dict, List, Any, Optional, Literal
import json
import traceback

from validation.unified_validator import UnifiedFAANGValidator
from validation.generic_validator_classes import collect_ontology_terms_from_experiments
from submission import BioSampleSubmitter, ExperimentSubmitter, AnalysisSubmitter

app = FastAPI(
    title="FAANG Validation API",
    description="API for validating FAANG sample and metadata submissions",
    version="1.0.0"
)

validator = UnifiedFAANGValidator()


class ValidationRequest(BaseModel):
    data: Dict[str, List[Dict[str, Any]]]
    validate_relationships: bool = True
    validate_ontology_text: bool = True
    data_type: Literal["sample", "experiment", "analysis"]


class ValidationResponse(BaseModel):
    status: str
    message: str
    results: Optional[Dict[str, Any]] = None
    report: Optional[str] = None


class ExperimentSubmissionRequest(BaseModel):
    validation_results: Dict[str, Any]
    original_data: Dict[str, Any]  # original json with experiment ena, run, study, submission sheets
    webin_username: str
    webin_password: str
    mode: str
    action: str = "submission"


class ExperimentSubmissionResponse(BaseModel):
    success: bool
    message: str
    submission_results: Optional[str] = None
    errors: Optional[List[str]] = None
    info_messages: Optional[List[str]] = None


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

# Health check endpoint
@app.get("/")
async def root():
    return {
        "status": "healthy",
        "service": "FAANG Validation API",
        "version": "1.0.0",
        "supported_types": validator.get_supported_types()
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "validators": {
            "sample_validators": len(validator.sample_validators),
            "metadata_validators": len(validator.metadata_validators),
            "experiment_validators": len(validator.experiment_validators),
            "analysis_validators": len(validator.analysis_validators)
        }
    }


@app.get("/supported-types")
async def get_supported_types():
    return validator.get_supported_types()


async def prefetch_data_by_type(data: Dict[str, List[Dict[str, Any]]], data_type: str):
    if data_type in ["sample"]:
        print("Pre-fetching sample ontology terms...")
        await validator.prefetch_all_ontology_terms_async("sample", data)

        print("Pre-fetching BioSample IDs...")
        await validator.prefetch_all_biosample_ids_async(data)

    if data_type in ["experiment"]:
        print("Pre-fetching experiment ontology terms...")
        await validator.prefetch_all_ontology_terms_async("experiment", data)

    if data_type == "analysis":
        # Analyses typically don't need pre-fetching
        print("Skipping pre-fetch for analysis data (no ontology terms or relationships)")


@app.post("/validate", response_model=ValidationResponse)
async def validate_data(request: ValidationRequest):
    try:
        await prefetch_data_by_type(request.data, request.data_type)

        print(f"Running validation for data_type: {request.data_type}...")
        results = validator.validate_all_records(
            request.data,
            validate_relationships=request.validate_relationships,
            validate_ontology_text=request.validate_ontology_text
        )

        # report
        report = validator.generate_unified_report(results)

        return ValidationResponse(
            status="success",
            message=f"Validation completed successfully for {request.data_type} data",
            results=results,
            report=report
        )

    except Exception as e:
        print(f"Error during validation: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Validation failed",
                "message": str(e),
                "type": type(e).__name__
            }
        )


@app.post("/submit-experiment", response_model=ExperimentSubmissionResponse)
def submit_experiment(request: ExperimentSubmissionRequest):
    try:
        if request.mode not in ["test", "prod"]:
            raise HTTPException(
                status_code=400,
                detail="Mode must be 'test' or 'prod'",
            )

        if request.action not in ["submission", "update"]:
            raise HTTPException(
                status_code=400,
                detail="Action must be 'submission' or 'update'",
            )

        print(f"Preparing experiment submission: mode={request.mode}, action={request.action}")

        # Prepare the results by adding ENA-specific sheets from original data
        prepared_results = dict(request.validation_results)

        # Add experiment ena records
        if 'experiment ena' in request.original_data:
            if 'experiment_results' not in prepared_results:
                prepared_results['experiment_results'] = {}
            if 'experiment ena' not in prepared_results['experiment_results']:
                prepared_results['experiment_results']['experiment ena'] = {'valid': [], 'invalid': []}

            for record in request.original_data['experiment ena']:
                normalized_record = normalize_experiment_ena_record(record)
                prepared_results['experiment_results']['experiment ena']['valid'].append({
                    'model': normalized_record,
                    'data': normalized_record
                })
            print(f"Added {len(request.original_data['experiment ena'])} experiment ena records")

        # Add run records
        if 'run' in request.original_data:
            if 'metadata_results' not in prepared_results:
                prepared_results['metadata_results'] = {}
            if 'run' not in prepared_results['metadata_results']:
                prepared_results['metadata_results']['run'] = {'valid': [], 'invalid': []}

            for record in request.original_data['run']:
                normalized_record = normalize_run_record(record)
                prepared_results['metadata_results']['run']['valid'].append({
                    'model': normalized_record,
                    'data': normalized_record
                })
            print(f"Added {len(request.original_data['run'])} run records")

        # Add study records
        if 'study' in request.original_data:
            if 'metadata_results' not in prepared_results:
                prepared_results['metadata_results'] = {}
            if 'study' not in prepared_results['metadata_results']:
                prepared_results['metadata_results']['study'] = {'valid': [], 'invalid': []}

            for record in request.original_data['study']:
                prepared_results['metadata_results']['study']['valid'].append({
                    'model': record,
                    'data': record
                })
            print(f"Added {len(request.original_data['study'])} study records")

        # Add submission records
        if 'submission' in request.original_data:
            if 'metadata_results' not in prepared_results:
                prepared_results['metadata_results'] = {}
            if 'submission' not in prepared_results['metadata_results']:
                prepared_results['metadata_results']['submission'] = {'valid': [], 'invalid': []}

            for record in request.original_data['submission']:
                prepared_results['metadata_results']['submission']['valid'].append({
                    'model': record,
                    'data': record
                })
            print(f"Added {len(request.original_data['submission'])} submission records")

        # Prepare credentials
        credentials = {
            "username": request.webin_username,
            "password": request.webin_password,
            "mode": request.mode
        }

        print(f"Submitting to ENA: mode={request.mode}, action={request.action}")

        # Initialize the experiment submitter
        submitter = ExperimentSubmitter()

        # Submit to ENA
        result = submitter.submit_to_ena(
            results=prepared_results,
            credentials=credentials,
            action=request.action
        )

        action_word = "update" if request.action == "update" else "submission"
        if result.get("success"):
            return ExperimentSubmissionResponse(
                success=True,
                message=result.get("message", f"Successful experiments {action_word} in ENA"),
                submission_results=result.get("submission_results"),
                errors=result.get("errors"),
                info_messages=result.get("info_messages"),
            )

        return ExperimentSubmissionResponse(
            success=False,
            message=result.get("message", f"Experiment {action_word} to ENA failed"),
            submission_results=result.get("submission_results"),
            errors=result.get("errors", ["Unknown error"]),
            info_messages=result.get("info_messages"),
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error during experiment {request.action}: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"Experiment {request.action} failed",
                "message": str(e),
                "type": type(e).__name__,
            },
        )

@app.post("/validate-file")
async def validate_file(
    file: UploadFile = File(...),
    data_type: Literal["sample", "experiment", "analysis"] = Query(
        ...,
        description="Type of data in the file: 'sample', 'experiment', or 'analysis'"
    ),
    validate_relationships: bool = Query(
        default=True,
        description="Whether to validate cross-record relationships"
    ),
    validate_ontology_text: bool = Query(
        default=True,
        description="Whether to validate ontology term text matches"
    )
):
    try:
        contents = await file.read()
        data = json.loads(contents)

        # Pre-fetch based on data type
        await prefetch_data_by_type(data, data_type)

        print(f"Running validation for data_type: {data_type}...")
        results = validator.validate_all_records(
            data,
            validate_relationships=validate_relationships,
            validate_ontology_text=validate_ontology_text
        )

        # Generate report
        report = validator.generate_unified_report(results)

        return {
            "status": "success",
            "filename": file.filename,
            "data_type": data_type,
            "message": f"File validated successfully as {data_type} data",
            "results": results,
            "report": report
        }

    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Invalid JSON file",
                "message": str(e)
            }
        )
    except Exception as e:
        print(f"Error during validation: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Validation failed",
                "message": str(e),
                "type": type(e).__name__
            }
        )


@app.get("/export-valid-samples")
async def export_valid_samples_endpoint():
    return {
        "message": "Use POST /validate endpoint first, then access results.biosample_exports from the response"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)