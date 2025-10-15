"""
FastAPI application for FAANG sample validation
Run with: uvicorn app:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import json
import traceback

from unified_validator import UnifiedFAANGValidator

app = FastAPI(
    title="FAANG Validation API",
    description="API for validating FAANG sample and metadata submissions",
    version="1.0.0"
)

# Initialize validator (singleton pattern)
validator = UnifiedFAANGValidator()


# Request/Response Models
class ValidationRequest(BaseModel):
    """Request body for validation endpoint"""
    data: Dict[str, List[Dict[str, Any]]]
    validate_relationships: bool = True
    validate_ontology_text: bool = True


class ValidationResponse(BaseModel):
    """Response model for validation results"""
    status: str
    message: str
    results: Optional[Dict[str, Any]] = None
    report: Optional[str] = None


# Health check endpoint
@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "FAANG Validation API",
        "version": "1.0.0",
        "supported_sample_types": validator.get_supported_types()['sample_types'],
        "supported_metadata_types": validator.get_supported_types()['metadata_types']
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "validators": {
            "sample_validators": len(validator.validators),
            "metadata_validators": len(validator.metadata_validators)
        }
    }


@app.get("/supported-types")
async def get_supported_types():
    """Get list of supported sample and metadata types"""
    return validator.get_supported_types()


@app.post("/validate", response_model=ValidationResponse)
async def validate_data(request: ValidationRequest):
    """
    Validate FAANG sample and metadata data

    **Parameters:**
    - data: Dictionary with sample/metadata type as key and list of records as value
    - validate_relationships: Whether to validate sample relationships (default: True)
    - validate_ontology_text: Whether to validate ontology text consistency (default: True)

    **Example Request:**
    ```json
    {
        "data": {
            "organism": [...],
            "submission": [...],
            "person": [...]
        },
        "validate_relationships": true,
        "validate_ontology_text": true
    }
    ```
    """
    try:
        # Pre-fetch ontology terms if validation is enabled
        if request.validate_ontology_text:
            print("Pre-fetching ontology terms...")
            await validator.prefetch_all_ontology_terms_async(request.data)

        # Pre-fetch BioSample IDs if relationship validation is enabled
        if request.validate_relationships:
            print("Pre-fetching BioSample IDs...")
            await validator.prefetch_all_biosample_ids_async(request.data)

        # Run validation
        print("Running validation...")
        results = validator.validate_all_records(
            request.data,
            validate_relationships=request.validate_relationships,
            validate_ontology_text=request.validate_ontology_text
        )

        # Generate report
        report = validator.generate_unified_report(results)

        return ValidationResponse(
            status="success",
            message="Validation completed successfully",
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
async def validate_file(file: UploadFile = File(...)):
    """
    Upload and validate a JSON file containing FAANG data

    **Parameters:**
    - file: JSON file containing sample/metadata data

    **Returns:**
    - Validation results and report
    """
    try:
        # Read and parse JSON file
        contents = await file.read()
        data = json.loads(contents)

        # Pre-fetch data (using async versions)
        print("Pre-fetching ontology terms...")
        await validator.prefetch_all_ontology_terms_async(data)

        print("Pre-fetching BioSample IDs...")
        await validator.prefetch_all_biosample_ids_async(data)

        # Run validation
        print("Running validation...")
        results = validator.validate_all_records(
            data,
            validate_relationships=True,
            validate_ontology_text=True
        )

        # Generate report
        report = validator.generate_unified_report(results)

        return {
            "status": "success",
            "filename": file.filename,
            "message": "File validated successfully",
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


@app.post("/validate-submission")
async def validate_submission_only(submission_data: List[Dict[str, Any]]):
    """Validate only submission metadata"""
    try:
        from metadata_validator import SubmissionValidator
        validator = SubmissionValidator()
        results = validator.validate_records(submission_data)
        report = validator.generate_validation_report(results)

        return {
            "status": "success",
            "results": results,
            "report": report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/validate-person")
async def validate_person_only(person_data: List[Dict[str, Any]]):
    """Validate only person metadata"""
    try:
        from metadata_validator import PersonValidator
        validator = PersonValidator()
        results = validator.validate_records(person_data)
        report = validator.generate_validation_report(results)

        return {
            "status": "success",
            "results": results,
            "report": report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/validate-organization")
async def validate_organization_only(organization_data: List[Dict[str, Any]]):
    """Validate only organization metadata"""
    try:
        from metadata_validator import OrganizationValidator
        validator = OrganizationValidator()
        results = validator.validate_records(organization_data)
        report = validator.generate_validation_report(results)

        return {
            "status": "success",
            "results": results,
            "report": report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/validate-samples/{sample_type}")
async def validate_specific_sample_type(
    sample_type: str,
    samples: List[Dict[str, Any]],
    validate_relationships: bool = True
):
    """
    Validate a specific sample type

    **Supported types:** organism, organoid, specimen from organism, cell line, etc.
    """
    try:
        if sample_type not in validator.validators:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported sample type: {sample_type}. Supported types: {list(validator.validators.keys())}"
            )

        sample_validator = validator.validators[sample_type]

        # Prepare data dict for validation
        all_samples = {sample_type: samples}

        results = sample_validator.validate_records(
            samples,
            validate_relationships=validate_relationships,
            all_samples=all_samples
        )

        report = sample_validator.generate_validation_report(results)

        return {
            "status": "success",
            "sample_type": sample_type,
            "results": results,
            "report": report
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/export-valid-samples")
async def export_valid_samples_endpoint():
    """
    Export valid samples to BioSample format
    Note: This requires validation to be run first
    """
    return {
        "message": "Use POST /validate endpoint first, then access results.biosample_exports from the response"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)