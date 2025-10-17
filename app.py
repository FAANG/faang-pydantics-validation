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

validator = UnifiedFAANGValidator()


class ValidationRequest(BaseModel):
    data: Dict[str, List[Dict[str, Any]]]
    validate_relationships: bool = True
    validate_ontology_text: bool = True


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
        "supported_sample_types": validator.get_supported_types()['sample_types'],
        "supported_metadata_types": validator.get_supported_types()['metadata_types']
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "validators": {
            "sample_validators": len(validator.validators),
            "metadata_validators": len(validator.metadata_validators)
        }
    }


@app.get("/supported-types")
async def get_supported_types():
    return validator.get_supported_types()


@app.post("/validate", response_model=ValidationResponse)
async def validate_data(request: ValidationRequest):
    try:
        if request.validate_ontology_text:
            print("Pre-fetching ontology terms...")
            await validator.prefetch_all_ontology_terms_async(request.data)

        if request.validate_relationships:
            print("Pre-fetching BioSample IDs...")
            await validator.prefetch_all_biosample_ids_async(request.data)

        print("Running validation...")
        results = validator.validate_all_records(
            request.data,
            validate_relationships=request.validate_relationships,
            validate_ontology_text=request.validate_ontology_text
        )

        # report
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


@app.get("/export-valid-samples")
async def export_valid_samples_endpoint():
    return {
        "message": "Use POST /validate endpoint first, then access results.biosample_exports from the response"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)