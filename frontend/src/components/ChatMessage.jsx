import React, { useState } from 'react';

function ResultsTable({ columns, rows, rowCount, executionTime, truncated }) {
  if (!columns || columns.length === 0) return null;

  return (
    <div className="response-card">
      <div className="card-header">
        <span className="icon">📊</span> Results
      </div>
      <div className="results-table-wrapper">
        <table className="results-table">
          <thead>
            <tr>
              {columns.map((col, i) => (
                <th key={i}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i}>
                {row.map((val, j) => (
                  <td key={j} title={String(val ?? '')}>
                    {val === null ? <em style={{ color: 'var(--text-muted)' }}>NULL</em> : String(val)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="results-meta">
        <span>{rowCount} row{rowCount !== 1 ? 's' : ''}{truncated ? '+' : ''}</span>
        {executionTime && <span>{executionTime}ms</span>}
      </div>
    </div>
  );
}

export default function ChatMessage({ message }) {
  const [showSql, setShowSql] = useState(true);

  if (message.role === 'user') {
    return (
      <div className="message message-user">
        <div className="bubble">{message.content}</div>
      </div>
    );
  }

  // Assistant message
  const data = message.data || {};
  const { sql, explanation, results, nl_answer, tables_used, error, retries } = data;

  return (
    <div className="message message-assistant">
      <div className="assistant-content">
        {/* Error */}
        {error && (
          <div className="error-msg">⚠️ {error}</div>
        )}

        {/* Natural Language Answer */}
        {nl_answer && (
          <div className="response-card">
            <div className="card-header">
              <span className="icon">💬</span> Answer
            </div>
            <div className="card-body nl-answer">{nl_answer}</div>
          </div>
        )}

        {/* SQL */}
        {sql && (
          <div className="response-card">
            <div className="card-header" onClick={() => setShowSql(!showSql)} style={{ cursor: 'pointer' }}>
              <span className="icon">🔍</span> Generated SQL
              <span style={{ marginLeft: 'auto', fontSize: 11 }}>{showSql ? '▾' : '▸'}</span>
            </div>
            {showSql && (
              <div className="card-body">
                <pre className="sql-display">{sql}</pre>
              </div>
            )}
          </div>
        )}

        {/* Results Table */}
        {results && results.columns && results.columns.length > 0 && (
          <ResultsTable
            columns={results.columns}
            rows={results.rows || []}
            rowCount={results.row_count || 0}
            executionTime={results.execution_time_ms}
            truncated={results.truncated}
          />
        )}

        {/* Explanation */}
        {explanation && (
          <div className="response-card">
            <div className="card-header">
              <span className="icon">📖</span> Explanation
            </div>
            <div className="card-body explanation">{explanation}</div>
          </div>
        )}

        {/* Tables Used */}
        {tables_used && tables_used.length > 0 && (
          <div className="tags">
            {tables_used.map((t) => (
              <span className="tag tag-table" key={t}>{t}</span>
            ))}
            {retries > 0 && (
              <span className="tag" style={{ background: 'var(--red-dim)', color: 'var(--orange)', border: '1px solid var(--orange)' }}>
                {retries} retries
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
