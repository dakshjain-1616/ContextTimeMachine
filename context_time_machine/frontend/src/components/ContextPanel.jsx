/**
 * ContextPanel - Renders context window at selected turn
 */

import React, { useEffect, useState } from 'react';
import './ContextPanel.css';

function ContextPanel({ session, turnNumber }) {
  const [context, setContext] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!session || turnNumber === undefined) return;

    setLoading(true);
    fetch(`/api/session/${session}/turn/${turnNumber}`)
      .then(r => r.json())
      .then(data => {
        setContext(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error loading context:', err);
        setLoading(false);
      });
  }, [session, turnNumber]);

  if (!session) {
    return <div className="context-panel">Load a session to view context</div>;
  }

  if (loading) {
    return <div className="context-panel">Loading turn context...</div>;
  }

  if (!context) {
    return <div className="context-panel">No context available</div>;
  }

  const roleColors = {
    system: '#3b82f6',
    user: '#6b7280',
    assistant: '#22c55e',
    tool: '#f97316',
    tool_result: '#f97316',
  };

  return (
    <div className="context-panel">
      <div className="context-header">
        <h3>Context at Turn {context.turn_number}</h3>
        <div className="context-stats">
          <span>{context.total_tokens} / {context.model_limit} tokens</span>
          <span>{context.utilization_percent.toFixed(1)}% utilized</span>
        </div>
      </div>

      {context.messages.length > 0 && (
        <div className="context-limit-indicator">
          <div
            className="limit-line"
            style={{
              top: `${(context.distance_to_limit / context.model_limit) * 100}%`
            }}
            title="Context limit line"
          />
        </div>
      )}

      <div className="messages-list">
        {context.messages.map((msg, idx) => (
          <div
            key={idx}
            className="message-block"
            style={{ borderLeftColor: roleColors[msg.role] || '#9ca3af' }}
          >
            <div className="message-header">
              <span className="message-role">{msg.role}</span>
              <span className="message-position">
                {context.messages.length - idx - 1} steps from end
              </span>
              <span className="message-tokens">{msg.token_count} tokens</span>
            </div>
            <div className="message-content">
              {msg.content.substring(0, 200)}
              {msg.content.length > 200 && '...'}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default ContextPanel;
