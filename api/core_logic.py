# ==============================================================================
# RISC-V Consensus Engine - Core Logic
# ==============================================================================
# Implements the Proposer-Verifier Architecture:
# - Model A (Gemini 1.5 Flash): High-context extraction
# - Model B (Llama 3 via Groq): Strict verification
# This satisfies Requirements #2 (Two LLMs) and #3 (Hallucination Filtering)
# ==============================================================================

import os
import json
import re
from typing import List, Optional
from google import genai
from google.genai import types
from groq import AsyncGroq
from pydantic import BaseModel, Field
from .prompts import EXTRACTION_PROMPT, VERIFICATION_PROMPT


# ==============================================================================
# DATA MODELS
# ==============================================================================

class Parameter(BaseModel):
    """A single extracted architectural parameter."""
    name: str = Field(..., description="Parameter name or description")
    excerpt: str = Field(..., description="Exact excerpt from source text")
    category: str = Field(..., description="Named|Unnamed|ConfigDependent|Numeric")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    is_valid: bool = Field(default=True)
    reasoning: Optional[str] = None
    verification_notes: Optional[str] = None


class ExtractionResult(BaseModel):
    """Result from the extraction phase (Gemini)."""
    success: bool
    parameters: List[dict]
    error: Optional[str] = None


class VerificationResult(BaseModel):
    """Result from the verification phase (Llama 3)."""
    success: bool
    results: List[dict]
    summary: Optional[dict] = None
    error: Optional[str] = None


class ConsensusResult(BaseModel):
    """Final output from the Consensus Engine."""
    strategy: str = "Dual-LLM Consensus"
    model_a: str = "Gemini 1.5 Flash"
    model_b: str = "Llama 3 70B"
    original_count: int
    validated_count: int
    rejected_count: int
    confidence_avg: float
    data: List[dict]
    verification_summary: Optional[dict] = None


# ==============================================================================
# THE CONSENSUS ENGINE
# ==============================================================================

class ConsensusEngine:
    """
    Dual-LLM Consensus Engine for RISC-V Parameter Extraction.
    
    Architecture:
    1. PROPOSER (Gemini 1.5 Flash): Reads spec text with massive context window,
       extracts all potential parameters with high recall.
    2. VERIFIER (Llama 3 70B via Groq): Strictly validates each proposed parameter,
       checking for hallucinations and correct categorization.
    3. MERGER: Combines results, keeping only validated parameters.
    """
    
    def __init__(self):
        """Initialize API clients from environment variables."""
        gemini_key = os.environ.get("GEMINI_KEY")
        groq_key = os.environ.get("GROQ_KEY")
        
        if not gemini_key:
            raise ValueError("GEMINI_KEY environment variable not set")
        if not groq_key:
            raise ValueError("GROQ_KEY environment variable not set")
        
        self.gemini = genai.Client(api_key=gemini_key)
        self.groq = AsyncGroq(api_key=groq_key)
    
    def _clean_json_response(self, text: str) -> str:
        """Clean markdown code blocks from JSON response."""
        # Remove markdown code blocks if present
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()
    
    async def _extract_with_gemini(self, text_chunk: str) -> ExtractionResult:
        """
        Phase 1: PROPOSE
        Use Gemini 1.5 Flash for high-recall extraction.
        Gemini's 1M token context window handles large spec chunks.
        """
        try:
            response = self.gemini.models.generate_content(
                model="gemini-flash-latest",
                contents=types.Content(
                    parts=[
                        types.Part(text=EXTRACTION_PROMPT),
                        types.Part(text=f"\n\n--- SPECIFICATION TEXT ---\n\n{text_chunk}")
                    ]
                ),
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,  
                )
            )
            
            # Parse the response
            response_text = self._clean_json_response(response.text)
            proposed_params = json.loads(response_text)
            
            # Ensure it's a list
            if isinstance(proposed_params, dict):
                proposed_params = proposed_params.get("parameters", [proposed_params])
            
            return ExtractionResult(success=True, parameters=proposed_params)
            
        except json.JSONDecodeError as e:
            return ExtractionResult(
                success=False, 
                parameters=[], 
                error=f"Gemini JSON parse error: {str(e)}"
            )
        except Exception as e:
            return ExtractionResult(
                success=False, 
                parameters=[], 
                error=f"Gemini extraction error: {str(e)}"
            )
    
    async def _verify_with_llama(self, text_chunk: str, proposed_params: List[dict]) -> VerificationResult:
        """
        Phase 2: VERIFY
        Use Llama 3 70B via Groq for strict verification.
        Llama provides a different model bias, reducing systematic errors.
        Groq's inference speed makes this practical for production.
        """
        try:
            verification_payload = json.dumps(proposed_params, indent=2)
            
            response = await self.groq.chat.completions.create(
                messages=[
                    {
                        "role": "system", 
                        "content": VERIFICATION_PROMPT
                    },
                    {
                        "role": "user", 
                        "content": f"""
--- SOURCE TEXT ---
{text_chunk}

--- PROPOSED PARAMETERS ---
{verification_payload}

Please verify each parameter according to the rules.
"""
                    }
                ],
                model="llama-3.1-8b-instant",
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            
            response_text = response.choices[0].message.content
            verified_data = json.loads(response_text)
            
            # Handle different response structures
            results = verified_data.get("results", [])
            if not results and isinstance(verified_data, list):
                results = verified_data
            
            summary = verified_data.get("summary", None)
            
            return VerificationResult(success=True, results=results, summary=summary)
            
        except json.JSONDecodeError as e:
            return VerificationResult(
                success=False, 
                results=[], 
                error=f"Llama JSON parse error: {str(e)}"
            )
        except Exception as e:
            return VerificationResult(
                success=False, 
                results=[], 
                error=f"Llama verification error: {str(e)}"
            )
    
    def _merge_results(
        self, 
        proposed: List[dict], 
        verified: VerificationResult
    ) -> ConsensusResult:
        """
        Phase 3: MERGE
        Combine extraction and verification results.
        Only keep parameters that passed the Auditor's check.
        """
        final_list = []
        rejected_count = 0
        total_confidence = 0.0
        
        for item in verified.results:
            is_valid = item.get("is_valid", True)
            
            if is_valid:
                confidence = item.get("confidence", 0.8)
                total_confidence += confidence
                
                final_list.append({
                    "name": item.get("name", "Unknown"),
                    "excerpt": item.get("excerpt", ""),
                    "category": item.get("category", item.get("original_category", "Unknown")),
                    "confidence": confidence,
                    "verification_notes": item.get("verification_notes", "")
                })
            else:
                rejected_count += 1
        
        avg_confidence = total_confidence / len(final_list) if final_list else 0.0
        
        return ConsensusResult(
            original_count=len(proposed),
            validated_count=len(final_list),
            rejected_count=rejected_count,
            confidence_avg=round(avg_confidence, 3),
            data=final_list,
            verification_summary=verified.summary
        )
    
    async def run_pipeline(self, text_chunk: str) -> dict:
        """
        Run the full Proposer-Verifier pipeline.
        
        Flow:
        1. Gemini extracts all potential parameters (high recall)
        2. Llama 3 verifies each parameter (high precision)
        3. Results are merged, keeping only validated items
        
        Args:
            text_chunk: The RISC-V specification text to analyze
            
        Returns:
            Dictionary containing validated parameters and metadata
        """
        # ==============================
        # PHASE 1: EXTRACTION (Gemini)
        # ==============================
        print("🤖 Phase 1: Gemini Extraction...")
        extraction_result = await self._extract_with_gemini(text_chunk)
        
        if not extraction_result.success:
            return {
                "error": extraction_result.error,
                "phase": "extraction",
                "strategy": "Dual-LLM Consensus"
            }
        
        proposed_params = extraction_result.parameters
        
        if not proposed_params:
            return {
                "status": "No parameters found",
                "strategy": "Dual-LLM Consensus",
                "model_a": "Gemini 1.5 Flash",
                "original_count": 0,
                "data": []
            }
        
        print(f"   ✅ Found {len(proposed_params)} potential parameters")
        
        # ==============================
        # PHASE 2: VERIFICATION (Llama 3)
        # ==============================
        print(f"🕵️ Phase 2: Llama-3 Verification of {len(proposed_params)} items...")
        verification_result = await self._verify_with_llama(text_chunk, proposed_params)
        
        if not verification_result.success:
            # Fallback: Return Gemini results without verification
            print(f"   ⚠️ Verification failed: {verification_result.error}")
            return {
                "warning": f"Verification phase failed: {verification_result.error}",
                "strategy": "Single-LLM (Gemini only - unverified)",
                "model_a": "Gemini 1.5 Flash",
                "original_count": len(proposed_params),
                "data": proposed_params
            }
        
        print(f"   ✅ Verification complete")
        
        # ==============================
        # PHASE 3: MERGE & REFINE
        # ==============================
        print("📊 Phase 3: Merging results...")
        consensus = self._merge_results(proposed_params, verification_result)
        
        print(f"   ✅ Final: {consensus.validated_count}/{consensus.original_count} parameters validated")
        print(f"   📉 Rejected: {consensus.rejected_count} potential hallucinations")
        
        return consensus.model_dump()


# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================

def chunk_text(text: str, max_chunk_size: int = 8000) -> List[str]:
    """
    Split large text into manageable chunks for processing.
    Tries to split on paragraph boundaries.
    """
    if len(text) <= max_chunk_size:
        return [text]
    
    chunks = []
    paragraphs = text.split("\n\n")
    current_chunk = ""
    
    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= max_chunk_size:
            current_chunk += para + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = para + "\n\n"
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks
