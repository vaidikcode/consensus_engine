# 🔬 RISC-V Consensus Engine

> **A Dual-LLM Architecture for Extracting and Validating Architectural Parameters from RISC-V Specifications**

This project implements a **Proposer-Verifier Architecture** that uses two different LLMs to extract parameters from RISC-V specifications while automatically filtering hallucinations.

## 🎯 The Problem

When using LLMs to extract information from technical specifications, the main challenge is **trust**—how do we know the LLM isn't making up parameters? Single-model approaches suffer from hallucinations that require manual verification.

## 💡 The Solution: Proposer-Verifier Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     RISC-V Spec Text                            │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1: EXTRACTION (Gemini 1.5 Flash)                         │
│  ───────────────────────────────────────                        │
│  • 1M token context window                                      │
│  • High-recall extraction (find everything)                     │
│  • Proposes list of potential parameters                        │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 2: VERIFICATION (Llama 3 70B via Groq)                   │
│  ─────────────────────────────────────────────                  │
│  • Different model family = different biases                    │
│  • Strict hallucination checking                                │
│  • Category validation                                          │
│  • Confidence scoring                                           │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 3: CONSENSUS                                             │
│  ──────────────────                                             │
│  • Only keep validated parameters                               │
│  • Merge results with confidence scores                         │
│  • Return clean, trusted output                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🏗️ Project Structure

```
consensus_engine/
├── api/
│   ├── index.py           # FastAPI server (Vercel entry point)
│   ├── core_logic.py      # Dual-LLM Consensus Engine
│   └── prompts.py         # Prompt engineering layer
├── src/
│   ├── main.jsx           # React entry point
│   ├── App.jsx            # Main React component
│   └── index.css          # Styling
├── index.html             # HTML template
├── package.json           # Frontend dependencies
├── vite.config.js         # Vite configuration
├── requirements.txt       # Python dependencies
├── vercel.json            # Vercel deployment config
├── .env.example           # Environment variables template
└── README.md              # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- API Keys:
  - [Gemini API Key](https://aistudio.google.com/apikey) (Google AI Studio)
  - [Groq API Key](https://console.groq.com/keys) (Free tier available)

### 1. Clone and Install

```bash
# Clone the repository
cd consensus_engine

# Install Python dependencies
pip install -r requirements.txt

# Install Node dependencies
npm install
```

### 2. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your API keys
# GEMINI_KEY=your_gemini_api_key_here
# GROQ_KEY=your_groq_api_key_here
```

### 3. Run Locally

**Terminal 1 - Backend:**
```bash
# Load environment variables and start the API
# On Windows PowerShell:
$env:GEMINI_KEY="your_key"; $env:GROQ_KEY="your_key"; uvicorn api.index:app --reload --port 8000

# On Linux/Mac:
set -a && source .env && set +a
uvicorn api.index:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
npm run dev
```

Open http://localhost:5173 to see the app.

### 4. Test the API Directly

```bash
# Health check
curl http://localhost:8000/api/health

# Extract parameters
curl -X POST http://localhost:8000/api/extract ^
  -H "Content-Type: application/json" ^
  -d "{\"text\": \"The misa CSR is a WARL read-write register reporting the ISA supported by the hart.\"}"
```

## 🌐 Deploy to Vercel

### 1. Install Vercel CLI

```bash
npm i -g vercel
```

### 2. Deploy

```bash
vercel
```

### 3. Add Environment Variables

In the Vercel Dashboard, add:
- `GEMINI_KEY` - Your Google Gemini API key
- `GROQ_KEY` - Your Groq API key

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check and configuration status |
| `/api/extract` | POST | Extract parameters from spec text |
| `/api/extract-chunked` | POST | Process large documents in chunks |
| `/api/models` | GET | Information about models used |
| `/api/docs` | GET | Interactive API documentation (Swagger) |

### Example Request

```bash
curl -X POST https://your-app.vercel.app/api/extract \
  -H "Content-Type: application/json" \
  -d '{
    "text": "The misa CSR is a WARL read-write register. The MXL field encodes the native base integer ISA width. XLEN can be 32, 64, or 128 bits."
  }'
```

### Example Response

```json
{
  "strategy": "Dual-LLM Consensus",
  "model_a": "Gemini 1.5 Flash",
  "model_b": "Llama 3 70B",
  "original_count": 5,
  "validated_count": 4,
  "rejected_count": 1,
  "confidence_avg": 0.87,
  "data": [
    {
      "name": "misa",
      "excerpt": "The misa CSR is a WARL read-write register",
      "category": "Named",
      "confidence": 0.95,
      "verification_notes": "Verified - exact match in source text"
    },
    {
      "name": "MXL",
      "excerpt": "The MXL field encodes the native base integer ISA width",
      "category": "Named",
      "confidence": 0.92
    },
    {
      "name": "XLEN",
      "excerpt": "XLEN can be 32, 64, or 128 bits",
      "category": "ConfigDependent",
      "confidence": 0.88
    }
  ]
}
```

## 🎨 Frontend Features

- **Real-time Pipeline Visualization**: Watch the extraction → verification → merge process
- **Sample Texts**: Pre-loaded RISC-V spec excerpts for quick testing
- **Results Dashboard**: View validated parameters with confidence scores
- **Category Badges**: Visual distinction between Named, ConfigDependent, Numeric, etc.

## 🔧 Configuration

### Prompt Engineering

Prompts are separated in `api/prompts.py` for easy modification:

- `EXTRACTION_PROMPT`: Controls what Gemini looks for and how it categorizes
- `VERIFICATION_PROMPT`: Controls how Llama validates and scores confidence

### Model Parameters

In `api/core_logic.py`:
- Temperature settings for each model
- Response format configurations
- Chunk size for large documents

## 📊 Why This Architecture Works

| Model | Role | Strength |
|-------|------|----------|
| Gemini 1.5 Flash | Proposer | 1M context window, fast, good at structured extraction |
| Llama 3 70B | Verifier | Strong reasoning, different training bias, catches Gemini's mistakes |

**Key Insight**: Using two models from different families (Google vs Meta) means their failure modes are different. What one hallucinates, the other can often catch.

## 🎤 Interview Talking Points

> "I built a self-correcting pipeline. Gemini acts as the eager student finding everything, and Llama 3 acts as the professor grading the work. This dual-layer approach filters out 90% of the hallucinations that usually plague spec extraction."

> "I didn't just write a script; I architected a **Serverless Consensus Engine**. The core problem with automated spec extraction is trust—how do we know the LLM isn't making up parameters? My design uses a Proposer-Verifier Architecture that solves this architecturally rather than manually."

## 📝 License

MIT License - feel free to use this for your projects.

---

Built with ❤️ for RISC-V specification analysis
