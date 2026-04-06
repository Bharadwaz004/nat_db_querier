import React, { useState } from 'react';

export default function Sidebar({ schema, connected }) {
  const [expanded, setExpanded] = useState({});

  const toggle = (table) => {
    setExpanded((prev) => ({ ...prev, [table]: !prev[table] }));
  };

  const tables = schema ? Object.entries(schema) : [];

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h1>⚡ NL→SQL</h1>
        <p>Hybrid RAG Query Assistant</p>
      </div>

      <div className="db-status">
        <span className={`db-badge ${connected ? 'connected' : 'disconnected'}`}>
          {connected ? '● Connected' : '○ Not connected'}
        </span>
      </div>

      <div className="schema-panel">
        {tables.length === 0 && (
          <p style={{ color: 'var(--text-muted)', fontSize: 13, padding: 8 }}>
            No schema loaded yet.
          </p>
        )}
        {tables.map(([table, info]) => (
          <div className="schema-table" key={table}>
            <div className="schema-table-name" onClick={() => toggle(table)}>
              <span>{expanded[table] ? '▾' : '▸'} {table}</span>
              <span className="row-count">{info.row_count} rows</span>
            </div>
            {expanded[table] && (
              <div className="schema-columns">
                {(info.columns || []).map((col) => (
                  <div key={col}>
                    {col} <span className="col-type"></span>
                  </div>
                ))}
                {(info.foreign_keys || []).length > 0 && (
                  <div style={{ marginTop: 4, color: 'var(--orange)', fontSize: 11 }}>
                    FK: {info.foreign_keys.map(
                      (fk) => `${fk.from_column} → ${fk.to_table}`
                    ).join(', ')}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </aside>
  );
}
