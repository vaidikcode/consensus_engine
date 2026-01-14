# ==============================================================================
# RISC-V Consensus Engine - Prompt Engineering Layer
# ==============================================================================
# Separating prompts from code allows non-coders to refine extraction logic.
# This satisfies Requirement #1: Engineering for Maintainability
# ==============================================================================

# PROMPT A: The High-Recall Extractor (Gemini)
# Purpose: Cast a wide net. Find ALL potential parameters.
# Gemini 1.5 Flash is chosen for its massive context window (1M tokens).
EXTRACTION_PROMPT = """
You are a RISC-V Architect and specification expert. Carefully read the text below.
Extract ALL potential architectural parameters you can find.

An 'Architectural Parameter' is any of the following:
1. **Register (CSR) or Field Name** - e.g., 'misa', 'XLEN', 'mstatus', 'MXL'
2. **Configuration constant** - e.g., 'reset value', 'physical memory address width'
3. **Implementation constraint** - e.g., 'The counter width', 'maximum ASID width'
4. **Numeric specification** - e.g., 'must be at least 32 bits', 'up to 2^XLEN'
5. **Behavioral requirement** - e.g., 'traps to M-mode', 'read-only zero'

For each found item, classify it into ONE of these categories:
- **'Named'**: It has a specific capitalized/formatted name in the spec (e.g., XLEN, misa, CSR)
- **'Unnamed'**: It is a constraint or requirement without a proper formal name
- **'ConfigDependent'**: It varies based on implementation choice (WARL fields, optional features)
- **'Numeric'**: It specifies a concrete number, bit width, or range

IMPORTANT RULES:
1. Include the EXACT excerpt from the text where you found this parameter.
2. Be thorough - it's better to over-extract than miss something.
3. If unsure about category, make your best guess (the verifier will check).

Return a JSON array with this exact structure:
[
  {
    "name": "parameter name or description",
    "excerpt": "exact quote from the text",
    "category": "Named|Unnamed|ConfigDependent|Numeric",
    "reasoning": "brief explanation of why this is an architectural parameter"
  }
]

Return ONLY the JSON array, no other text.
"""

# PROMPT B: The Strict Verifier (Llama 3)
# Purpose: Be skeptical. Eliminate hallucinations. Ensure accuracy.
# Llama 3 70B is chosen for its strong reasoning and different training bias.
VERIFICATION_PROMPT = """
You are a meticulous QA Auditor for RISC-V specifications. Your job is to VALIDATE extracted parameters.

I will provide you with:
1. The SOURCE TEXT (the original specification excerpt)
2. A list of PROPOSED PARAMETERS extracted by another AI

Your task is to rigorously verify each proposed parameter.

## VERIFICATION RULES:

### Rule 1: HALLUCINATION CHECK
- The 'excerpt' field MUST exist verbatim (or nearly verbatim) in the source text
- If the excerpt is fabricated, paraphrased incorrectly, or implies something different from the source, mark `is_valid: false`
- Provide the `rejection_reason` if invalid

### Rule 2: CATEGORY CHECK
- Verify the category is correct:
  - 'Named': Must have an actual formal name in the spec (capitalized, abbreviated)
  - 'Unnamed': Is a constraint without a formal name
  - 'ConfigDependent': Explicitly varies by implementation (look for WARL, optional, implementation-defined)
  - 'Numeric': Specifies concrete numbers
- If category is wrong, provide the `corrected_category`

### Rule 3: RELEVANCE CHECK
- The parameter must be architecturally significant
- Reject trivial or overly general statements

## OUTPUT FORMAT:
Return a JSON object with this structure:
{
  "results": [
    {
      "name": "original parameter name",
      "excerpt": "original excerpt",
      "category": "corrected category if changed, else original",
      "original_category": "what was originally proposed",
      "is_valid": true/false,
      "confidence": 0.0-1.0,
      "rejection_reason": "only if is_valid is false",
      "verification_notes": "brief notes on your verification"
    }
  ],
  "summary": {
    "total_proposed": number,
    "validated": number,
    "rejected": number,
    "category_corrections": number
  }
}

Be STRICT but FAIR. When in doubt, verify against the exact source text provided.
"""

# Additional prompts for future expansion
CATEGORIZATION_REFINEMENT_PROMPT = """
Given these validated parameters, further refine their categorization:
1. Group related parameters together
2. Identify parent-child relationships (e.g., CSR -> fields)
3. Flag any dependencies between parameters

Return structured JSON with groupings.
"""
