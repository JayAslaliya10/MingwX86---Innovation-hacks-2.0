import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { uploadPolicies } from '../api/client'

export default function Upload() {
  const navigate = useNavigate()
  const [files, setFiles] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [dragging, setDragging] = useState(false)

  const addFiles = (newFiles) => {
    const pdfs = Array.from(newFiles).filter((f) => f.type === 'application/pdf')
    setFiles((prev) => [...prev, ...pdfs])
  }

  const onDrop = useCallback((e) => {
    e.preventDefault()
    setDragging(false)
    addFiles(e.dataTransfer.files)
  }, [])

  const handleSubmit = async () => {
    if (!files.length) return
    setLoading(true)
    setError(null)
    try {
      await uploadPolicies(files)
      navigate('/dashboard')
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center py-12 px-4">
      <div className="card w-full max-w-xl">
        <h2 className="text-2xl font-bold text-gray-900 mb-1">Upload Policy Documents</h2>
        <p className="text-gray-500 text-sm mb-6">
          Upload one or more medical benefit drug policy PDFs. Our AI will extract and analyze them automatically.
        </p>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 mb-4 text-sm">
            {error}
          </div>
        )}

        {/* Drop Zone */}
        <div
          onDrop={onDrop}
          onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          className={`border-2 border-dashed rounded-xl p-10 text-center transition-colors cursor-pointer
            ${dragging ? 'border-brand-500 bg-brand-50' : 'border-gray-300 hover:border-brand-400'}`}
          onClick={() => document.getElementById('file-input').click()}
        >
          <div className="text-4xl mb-3">📄</div>
          <p className="text-gray-600 font-medium">Drop PDFs here or click to browse</p>
          <p className="text-gray-400 text-xs mt-1">Supports text PDFs and scanned image PDFs</p>
          <input
            id="file-input"
            type="file"
            accept="application/pdf"
            multiple
            className="hidden"
            onChange={(e) => addFiles(e.target.files)}
          />
        </div>

        {/* File List */}
        {files.length > 0 && (
          <div className="mt-4 space-y-2">
            {files.map((f, i) => (
              <div key={i} className="flex items-center justify-between bg-gray-50 rounded-lg px-4 py-2 border">
                <div className="flex items-center gap-2">
                  <span className="text-red-500">📕</span>
                  <span className="text-sm text-gray-700 truncate max-w-xs">{f.name}</span>
                  <span className="text-xs text-gray-400">({(f.size / 1024).toFixed(0)} KB)</span>
                </div>
                <button
                  onClick={() => setFiles((prev) => prev.filter((_, j) => j !== i))}
                  className="text-gray-400 hover:text-red-500 text-sm"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="flex gap-3 mt-6">
          <button
            onClick={handleSubmit}
            disabled={!files.length || loading}
            className="btn-primary flex-1 py-3"
          >
            {loading ? 'Uploading & Analyzing...' : `Upload ${files.length || ''} Document${files.length !== 1 ? 's' : ''}`}
          </button>
        </div>

        {loading && (
          <p className="text-xs text-gray-500 text-center mt-3">
            AI is parsing your documents. This may take a minute...
          </p>
        )}
      </div>
    </div>
  )
}
