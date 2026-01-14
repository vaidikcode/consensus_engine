import { useState } from 'react'

// Sample RISC-V spec texts for demo
const SAMPLE_TEXTS = {
  misa: `The misa CSR is a WARL read-write register reporting the ISA supported by the hart. The MXL field encodes the native base integer ISA width as shown in Table 3.1. The MXL field may be writable on implementations that support multiple base ISAs. The effective XLEN in M-mode, MXLEN, is given by the setting of MXL, or is a fixed constant on implementations that only support one base ISA.

The misa register must be readable in any implementation, but a value of zero can be returned to indicate the misa register has not been implemented, requiring that CPU capabilities be determined through a separate non-standard mechanism.

The Extensions field encodes the presence of the standard extensions, with a single bit per letter of the alphabet (bit 0 encodes presence of extension "A", bit 1 encodes presence of extension "B", through to bit 25 which encodes "Z"). The "I" bit will be set for RV32I, RV64I, RV128I base ISAs, and the "E" bit will be set for RV32E, RV64E, RV128E base ISAs.`,

  csr: `Machine-level CSRs are typically accessible at any privilege level, although the behavior at lower privilege levels may be different. The RISC-V ISA reserves a 12-bit encoding space (csr[11:0]) for up to 4,096 CSRs.

The reset value of the mstatus register is implementation-specific but must satisfy the following constraints: machine mode must be the current operating mode (MPP=3), interrupt enable bits (MIE, SIE, UIE) must be 0, and the privilege mode must be set to M-mode.

The mcause register is an MXLEN-bit read-write register. When a trap is taken into M-mode, mcause is written with a code indicating the event that caused the trap. The Interrupt bit in the mcause register is set if the trap was caused by an interrupt.`,

  counter: `The RISC-V ISA provides a set of up to 32×64-bit performance counters and timers, with the counter values accessible via unprivileged XLEN-bit read-only CSRs. The first three of these counters (CYCLE, TIME, INSTRET) have dedicated functions, while the remaining 29 (hpmcounter3-hpmcounter31) are programmable event counters.

For RV32, the upper 32 bits of all 64-bit counters are accessible via additional CSRs with an 'H' suffix (CYCLEH, TIMEH, INSTRETH, hpmcounter3h-hpmcounter31h).

The time CSR counts wall-clock real time that has passed from an arbitrary start time in the past. The rate at which time advances is implementation-defined, but must be a constant rate that is at least 10^6 ticks per second.`
}

function App() {
  const [inputText, setInputText] = useState('')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [pipelineState, setPipelineState] = useState({
    extraction: 'idle',
    verification: 'idle',
    merge: 'idle'
  })

  const handleExtract = async () => {
    if (!inputText.trim()) {
      setError('Please enter some RISC-V specification text')
      return
    }

    setLoading(true)
    setError(null)
    setResults(null)
    setPipelineState({ extraction: 'active', verification: 'idle', merge: 'idle' })

    try {
      // Simulate pipeline stages for UI feedback
      await new Promise(r => setTimeout(r, 500))
      setPipelineState({ extraction: 'active', verification: 'idle', merge: 'idle' })

      const response = await fetch('/api/extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: inputText })
      })

      if (!response.ok) {
        const errData = await response.json()
        throw new Error(errData.detail || 'Extraction failed')
      }

      setPipelineState({ extraction: 'completed', verification: 'active', merge: 'idle' })
      await new Promise(r => setTimeout(r, 300))
      
      setPipelineState({ extraction: 'completed', verification: 'completed', merge: 'active' })
      await new Promise(r => setTimeout(r, 200))

      const data = await response.json()
      setResults(data)
      setPipelineState({ extraction: 'completed', verification: 'completed', merge: 'completed' })

    } catch (err) {
      setError(err.message)
      setPipelineState({ extraction: 'error', verification: 'error', merge: 'error' })
    } finally {
      setLoading(false)
    }
  }

  const loadSample = (key) => {
    setInputText(SAMPLE_TEXTS[key])
    setResults(null)
    setError(null)
    setPipelineState({ extraction: 'idle', verification: 'idle', merge: 'idle' })
  }

  const clearAll = () => {
    setInputText('')
    setResults(null)
    setError(null)
    setPipelineState({ extraction: 'idle', verification: 'idle', merge: 'idle' })
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <h1>🔬 RISC-V Consensus Engine</h1>
        <p className="subtitle">
          Dual-LLM architecture for extracting and validating architectural parameters 
          from RISC-V specifications with automatic hallucination filtering.
        </p>
        <div className="architecture-badge">
          <span className="dot"></span>
          Proposer-Verifier Architecture
        </div>
      </header>

      {/* Main Grid */}
      <div className="main-grid">
        {/* Input Section */}
        <div className="card input-section">
          <div className="card-header">
            <h2 className="card-title">
              <span className="icon">📄</span>
              Specification Input
            </h2>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              {inputText.length} characters
            </span>
          </div>
          
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Paste RISC-V specification text here...

The engine will extract all architectural parameters (CSRs, registers, configuration constants, implementation constraints) and validate them using dual-LLM consensus."
          />
          
          <div className="input-actions">
            <button 
              className="btn btn-primary" 
              onClick={handleExtract}
              disabled={loading || !inputText.trim()}
            >
              {loading ? (
                <>
                  <span className="spinner"></span>
                  Processing...
                </>
              ) : (
                <>🚀 Extract Parameters</>
              )}
            </button>
            <button className="btn btn-secondary" onClick={clearAll}>
              Clear
            </button>
          </div>

          <div className="sample-texts">
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginRight: '0.5rem' }}>
              Try samples:
            </span>
            <button className="sample-btn" onClick={() => loadSample('misa')}>
              misa CSR
            </button>
            <button className="sample-btn" onClick={() => loadSample('csr')}>
              Machine CSRs
            </button>
            <button className="sample-btn" onClick={() => loadSample('counter')}>
              Performance Counters
            </button>
          </div>
        </div>

        {/* Pipeline Visualization */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">
              <span className="icon">⚙️</span>
              Processing Pipeline
            </h2>
          </div>
          
          <div className="pipeline-viz">
            {/* Step 1: Gemini Extraction */}
            <div className={`pipeline-step ${pipelineState.extraction}`}>
              <div className="step-icon gemini">🤖</div>
              <div className="step-content">
                <div className="step-title">Phase 1: Extraction</div>
                <div className="step-desc">Gemini 1.5 Flash • High-recall parameter discovery</div>
              </div>
              <div className={`step-status ${pipelineState.extraction}`}>
                {pipelineState.extraction === 'idle' && 'Waiting'}
                {pipelineState.extraction === 'active' && '⏳ Extracting...'}
                {pipelineState.extraction === 'completed' && '✓ Complete'}
                {pipelineState.extraction === 'error' && '✕ Failed'}
              </div>
            </div>

            {/* Step 2: Llama Verification */}
            <div className={`pipeline-step ${pipelineState.verification}`}>
              <div className="step-icon llama">🕵️</div>
              <div className="step-content">
                <div className="step-title">Phase 2: Verification</div>
                <div className="step-desc">Llama 3 70B • Strict hallucination check</div>
              </div>
              <div className={`step-status ${pipelineState.verification}`}>
                {pipelineState.verification === 'idle' && 'Waiting'}
                {pipelineState.verification === 'active' && '⏳ Verifying...'}
                {pipelineState.verification === 'completed' && '✓ Complete'}
                {pipelineState.verification === 'error' && '✕ Failed'}
              </div>
            </div>

            {/* Step 3: Merge */}
            <div className={`pipeline-step ${pipelineState.merge}`}>
              <div className="step-icon merge">📊</div>
              <div className="step-content">
                <div className="step-title">Phase 3: Consensus</div>
                <div className="step-desc">Merge validated results only</div>
              </div>
              <div className={`step-status ${pipelineState.merge}`}>
                {pipelineState.merge === 'idle' && 'Waiting'}
                {pipelineState.merge === 'active' && '⏳ Merging...'}
                {pipelineState.merge === 'completed' && '✓ Complete'}
                {pipelineState.merge === 'error' && '✕ Failed'}
              </div>
            </div>

            {/* Architecture Info */}
            <div style={{ 
              marginTop: 'auto', 
              padding: '1rem', 
              background: 'var(--bg-tertiary)', 
              borderRadius: '0.5rem',
              fontSize: '0.8rem',
              color: 'var(--text-secondary)'
            }}>
              <strong style={{ color: 'var(--text-primary)' }}>Why two models?</strong>
              <p style={{ marginTop: '0.5rem' }}>
                Gemini acts as the "eager student" finding everything, while Llama 3 acts as the 
                "strict professor" grading the work. This dual-layer approach filters out hallucinations 
                that usually plague spec extraction.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Results Section */}
      {results && (
        <div className="results-section card">
          <div className="results-header">
            <h2 className="card-title">
              <span className="icon">✅</span>
              Extraction Results
            </h2>
            <div className="results-stats">
              <div className="stat">
                <div className="stat-value">{results.original_count || 0}</div>
                <div className="stat-label">Proposed</div>
              </div>
              <div className="stat">
                <div className="stat-value validated">{results.validated_count || results.data?.length || 0}</div>
                <div className="stat-label">Validated</div>
              </div>
              <div className="stat">
                <div className="stat-value rejected">{results.rejected_count || 0}</div>
                <div className="stat-label">Rejected</div>
              </div>
              {results.confidence_avg && (
                <div className="stat">
                  <div className="stat-value">{Math.round(results.confidence_avg * 100)}%</div>
                  <div className="stat-label">Avg Confidence</div>
                </div>
              )}
            </div>
          </div>

          {results.data && results.data.length > 0 ? (
            <div className="parameters-grid">
              {results.data.map((param, idx) => (
                <div key={idx} className="param-card">
                  <div className="param-header">
                    <span className="param-name">{param.name}</span>
                    <span className={`param-category ${param.category}`}>
                      {param.category}
                    </span>
                  </div>
                  <div className="param-excerpt">
                    "{param.excerpt}"
                  </div>
                  {param.confidence !== undefined && (
                    <div className="param-confidence">
                      <span>Confidence:</span>
                      <div className="confidence-bar">
                        <div 
                          className="confidence-fill" 
                          style={{ width: `${(param.confidence || 0.8) * 100}%` }}
                        ></div>
                      </div>
                      <span>{Math.round((param.confidence || 0.8) * 100)}%</span>
                    </div>
                  )}
                  {param.verification_notes && (
                    <p style={{ 
                      fontSize: '0.75rem', 
                      color: 'var(--text-muted)', 
                      marginTop: '0.5rem' 
                    }}>
                      📝 {param.verification_notes}
                    </p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <div className="icon">📭</div>
              <p>No validated parameters found in this text.</p>
            </div>
          )}
        </div>
      )}

      {/* Footer */}
      <footer className="footer">
        <p>
          <strong>RISC-V Consensus Engine</strong> — Dual-LLM Architecture for Spec Extraction
        </p>
        <p style={{ marginTop: '0.5rem' }}>
          Built with Gemini 1.5 Flash + Llama 3 70B | 
          <a href="/api/docs" target="_blank" rel="noopener"> API Docs</a> | 
          <a href="/api/health" target="_blank" rel="noopener"> Health Check</a>
        </p>
      </footer>
    </div>
  )
}

export default App
