import { useState, useRef } from 'react';

export default function ConnectionModal({ onConnect, onUpload, onUseSample }) {
  const [mode, setMode] = useState(null); // null | 'connect' | 'upload'
  const [dbPath, setDbPath] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const fileRef = useRef();

  const handleConnect = async () => {
    if (!dbPath.trim()) return;
    setLoading(true);
    setError('');
    try {
      await onConnect(dbPath.trim());
    } catch (e) {
      setError(e.message);
    }
    setLoading(false);
  };

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setError('');
    try {
      await onUpload(file);
    } catch (e) {
      setError(e.message);
    }
    setLoading(false);
  };

  return (
    <div className="modal-overlay">
      <div className="modal">
        <h2>Connect Your Database</h2>
        <p>Choose how you'd like to get started with AskMyDB.</p>

        {error && <div className="error-msg" style={{ marginBottom: 12 }}>{error}</div>}

        {!mode && (
          <div className="modal-actions">
            <button className="modal-btn" onClick={onUseSample}>
              <span className="label">🎯 Use Sample Database</span>
              <span className="desc">Pre-loaded e-commerce dataset — great for trying things out</span>
            </button>
            <button className="modal-btn" onClick={() => setMode('upload')}>
              <span className="label">📂 Upload SQLite File</span>
              <span className="desc">Upload a .db, .sqlite, or .sqlite3 file</span>
            </button>
            <button className="modal-btn" onClick={() => setMode('connect')}>
              <span className="label">🔌 Connect by Path</span>
              <span className="desc">Enter the path to an existing SQLite database</span>
            </button>
          </div>
        )}

        {mode === 'connect' && (
          <div>
            <input
              className="input-field"
              placeholder="/path/to/database.db"
              value={dbPath}
              onChange={(e) => setDbPath(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleConnect()}
              autoFocus
            />
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="send-btn" onClick={handleConnect} disabled={loading}>
                {loading ? 'Connecting…' : 'Connect'}
              </button>
              <button className="modal-btn" onClick={() => setMode(null)} style={{ flex: 0 }}>
                Back
              </button>
            </div>
          </div>
        )}

        {mode === 'upload' && (
          <div>
            <input
              type="file"
              accept=".db,.sqlite,.sqlite3"
              ref={fileRef}
              onChange={handleUpload}
              style={{ display: 'none' }}
            />
            <button
              className="modal-btn"
              onClick={() => fileRef.current?.click()}
              disabled={loading}
              style={{ width: '100%' }}
            >
              <span className="label">{loading ? 'Uploading…' : 'Choose File'}</span>
              <span className="desc">.db, .sqlite, .sqlite3</span>
            </button>
            <button
              className="modal-btn"
              onClick={() => setMode(null)}
              style={{ width: '100%', marginTop: 8 }}
            >
              Back
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
