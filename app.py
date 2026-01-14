from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from pydantic import BaseModel
from typing import Dict, List, Any, Optional, Literal
import json
import traceback

from validation.unified_validator import UnifiedFAANGValidator
from validation.generic_validator_classes import collect_ontology_terms_from_experiments

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
            # "status": "success",
            # "filename": file.filename,
            # "data_type": data_type,
            # "message": f"File validated successfully as {data_type} data",
            # "results": results,
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
@app.post("/validate-file_old")
async def validate_file(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        data = json.loads(contents)

        print("Pre-fetching ontology terms...")
        await validator.prefetch_all_ontology_terms_async(data)

        print("Pre-fetching BioSample IDs...")
        await validator.prefetch_all_biosample_ids_async(data)

        print("Running validation...")
        results = validator.validate_all_records(
            data,
            validate_relationships=True,
            validate_ontology_text=True
        )

        # report
        report = validator.generate_unified_report(results)

        # return data

        return {
            # "status": "success",
            # "filename": file.filename,
            # "message": "File validated successfully",
            # "results": results,
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