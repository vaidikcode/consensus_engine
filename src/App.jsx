import { useState } from 'react'

function App() {
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  const onSubmit = async (e) => {
    e.preventDefault()

    const trimmed = text.trim()
    if (trimmed.length < 10) {
      setError('Please paste at least 10 characters of spec text.')
      return
    }

    setLoading(true)
    setError('')
    setResult(null)

    try {
      const resp = await fetch('/api/extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: trimmed }),
      })

      const data = await resp.json()
      if (!resp.ok) {
        throw new Error(data?.detail || 'Request failed')
      }

      setResult(data)
    } catch (err) {
      setError(err?.message || 'Unexpected error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container">
      <h1>RISC-V Consensus Engine</h1>
      <p className="muted">Paste spec text → POST /api/extract → view JSON result.</p>

      <form onSubmit={onSubmit} className="panel">
        <label className="label" htmlFor="specText">Spec text</label>
        <textarea
          id="specText"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste RISC-V spec text here..."
          rows={12}
        />

        <div className="actions">
          <button type="submit" disabled={loading}>
            {loading ? 'Extracting…' : 'Extract'}
          </button>
          <button
            type="button"
            className="secondary"
            onClick={() => {
              setText('')
              setError('')
              setResult(null)
            }}
            disabled={loading}
          >
            Clear
          </button>
          <a className="link" href="/api/docs" target="_blank" rel="noreferrer">API docs</a>
        </div>
      </form>

      {error ? <div className="error">{error}</div> : null}

      {result ? (
        <div className="panel">
          <div className="row">
            <h2>Result</h2>
            {'validated_count' in result ? (
              <span className="badge">
                validated: {result.validated_count} / proposed: {result.original_count}
              </span>
            ) : null}
          </div>
          <pre className="pre">{JSON.stringify(result, null, 2)}</pre>
        </div>
      ) : null}
    </div>
  )
}

export default App
