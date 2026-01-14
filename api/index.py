# ==============================================================================
# RISC-V Consensus Engine - FastAPI Server
# ==============================================================================
# Main entry point for the Vercel serverless deployment.
# Exposes the Dual-LLM pipeline as a REST API.
# ==============================================================================

from fastapi import FastAPI, HTTPException, Body, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import os

from .core_logic import ConsensusEngine, chunk_text

# ==============================================================================
# APP CONFIGURATION
# ==============================================================================

app = FastAPI(
    title="RISC-V Parameter Extractor",
    description="""
## Dual-LLM Consensus Engine for RISC-V Specification Analysis

This API uses a **Proposer-Verifier Architecture** to extract and validate 
architectural parameters from RISC-V specification text.

### How it works:
1. **Gemini 1.5 Flash** (Proposer): Reads the spec with its massive context window and extracts all potential parameters
2. **Llama 3 70B** (Verifier): Validates each parameter, checking for hallucinations and correct categorization
3. **Consensus Merger**: Combines results, keeping only validated parameters

### Why this approach?
- Reduces hallucinations by cross-checking between two different model families
- High recall (Gemini finds everything) + High precision (Llama filters errors)
- Architecturally addresses the trust problem in automated spec extraction
    """,
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS Configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================================================
# REQUEST/RESPONSE MODELS
# ==============================================================================

class ExtractRequest(BaseModel):
    """Request body for the extraction endpoint."""
    text: str = Field(
        ..., 
        min_length=10,
        description="RISC-V specification text to analyze",
        json_schema_extra={
            "example": "The misa CSR is a WARL read-write register reporting the ISA supported by the hart. The MXL field encodes the native base integer ISA width as shown in Table 1."
        }
    )

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    system: str
    models: dict
    environment: str

class ExtractResponse(BaseModel):
    """Extraction response with validated parameters."""
    strategy: str
    model_a: str
    model_b: str
    original_count: int
    validated_count: int
    rejected_count: int
    confidence_avg: float
    data: list
    verification_summary: Optional[dict] = None

# ==============================================================================
# ENDPOINTS
# ==============================================================================

@app.get("/api/health", response_model=HealthResponse, tags=["System"])
def health_check():
    """
    Check the health status of the Consensus Engine.
    
    Returns configuration info and whether API keys are configured.
    """
    gemini_configured = bool(os.environ.get("GEMINI_KEY"))
    groq_configured = bool(os.environ.get("GROQ_KEY"))
    
    return HealthResponse(
        status="online" if (gemini_configured and groq_configured) else "degraded",
        system="Dual-LLM Consensus Engine",
        models={
            "proposer": {
                "name": "Gemini 1.5 Flash",
                "provider": "Google",
                "configured": gemini_configured
            },
            "verifier": {
                "name": "Llama 3 70B",
                "provider": "Groq",
                "configured": groq_configured
            }
        },
        environment="production" if os.environ.get("VERCEL") else "development"
    )


@app.post("/api/extract", tags=["Extraction"])
async def extract_parameters(payload: ExtractRequest):
    """
    Extract and validate RISC-V architectural parameters from specification text.
    
    ## Process:
    1. **Extraction Phase** (Gemini 1.5 Flash): Identifies all potential parameters
    2. **Verification Phase** (Llama 3 70B): Validates each parameter for accuracy
    3. **Consensus Phase**: Returns only validated parameters with confidence scores
    
    ## Parameters:
    - **text**: RISC-V specification text (minimum 10 characters)
    
    ## Returns:
    - Validated parameters with categories and confidence scores
    - Statistics on extraction vs. validation counts
    - Verification summary from the auditor model
    """
    if len(payload.text.strip()) < 10:
        raise HTTPException(
            status_code=400, 
            detail="Text too short. Please provide at least 10 characters of specification text."
        )
    
    try:
        engine = ConsensusEngine()
        result = await engine.run_pipeline(payload.text)
        return result
        
    except ValueError as e:
        # Missing API keys
        raise HTTPException(
            status_code=503,
            detail=f"Service configuration error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Processing error: {str(e)}"
        )


@app.post("/api/extract-chunked", tags=["Extraction"])
async def extract_parameters_chunked(payload: ExtractRequest):
    """
    Extract parameters from large specification text by processing in chunks.
    
    Use this endpoint for very large documents that might exceed model context limits.
    The text is split into manageable chunks, each processed independently, 
    and results are merged.
    """
    if len(payload.text.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Text too short."
        )
    
    try:
        engine = ConsensusEngine()
        chunks = chunk_text(payload.text, max_chunk_size=6000)
        
        all_results = []
        total_original = 0
        total_validated = 0
        total_rejected = 0
        
        for i, chunk in enumerate(chunks):
            print(f"Processing chunk {i+1}/{len(chunks)}...")
            result = await engine.run_pipeline(chunk)
            
            if "error" not in result:
                all_results.extend(result.get("data", []))
                total_original += result.get("original_count", 0)
                total_validated += result.get("validated_count", 0)
                total_rejected += result.get("rejected_count", 0)
        
        return {
            "strategy": "Dual-LLM Consensus (Chunked)",
            "model_a": "Gemini 1.5 Flash",
            "model_b": "Llama 3 70B",
            "chunks_processed": len(chunks),
            "original_count": total_original,
            "validated_count": total_validated,
            "rejected_count": total_rejected,
            "data": all_results
        }
        
    except ValueError as e:
        raise HTTPException(status_code=503, detail=f"Configuration error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@app.get("/api/models", tags=["System"])
def list_models():
    """
    List the models used in the Consensus Engine and their roles.
    """
    return {
        "architecture": "Proposer-Verifier",
        "models": [
            {
                "role": "Proposer",
                "name": "Gemini 1.5 Flash",
                "provider": "Google",
                "purpose": "High-recall extraction with massive context window",
                "context_window": "1M tokens",
                "characteristics": [
                    "Fast inference",
                    "Large context handling",
                    "Good at following structured output formats"
                ]
            },
            {
                "role": "Verifier",
                "name": "Llama 3 70B",
                "provider": "Groq",
                "purpose": "Strict validation and hallucination detection",
                "context_window": "8K tokens",
                "characteristics": [
                    "Strong reasoning capabilities",
                    "Different training bias than Gemini",
                    "Excellent at logical verification tasks"
                ]
            }
        ],
        "benefits": [
            "Cross-model validation reduces hallucinations",
            "Different model families catch different types of errors",
            "High recall + High precision through specialization"
        ]
    }


# ==============================================================================
# ROOT REDIRECT
# ==============================================================================

@app.get("/", tags=["System"])
def root():
    """Redirect to API documentation."""
    return {
        "message": "RISC-V Consensus Engine API",
        "docs": "/api/docs",
        "health": "/api/health"
    }
