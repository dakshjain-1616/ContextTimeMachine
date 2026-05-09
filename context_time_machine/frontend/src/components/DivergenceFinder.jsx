/**
 * DivergenceFinder - Two-session comparison and diff
 */

import React, { useState, useEffect } from 'react';
import './DivergenceFinder.css';

function DivergenceFinder() {
  const [sessions, setSessions] = useState([]);
  const [sessionAId, setSessionAId] = useState('');
  const [sessionBId, setSessionBId] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Load available sessions
    fetch('/api/sessions')
      .then(r => r.json())
      .then(data => setSessions(data.sessions || []))
      .catch(err => console.error('Error loading sessions:', err));
  }, []);

  const handleFindDivergence = async () => {
    if (!sessionAId || !sessionBId) return;

    setLoading(true);
    try {
      const response = await fetch('/api/divergence', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_a_id: sessionAId,
          session_b_id: sessionBId,
        }),
      });
      const data = await response.json();
      setResult(data);
    } catch (err) {
      console.error('Error finding divergence:', err);
    }
    setLoading(false);
  };

  return (
    <div className="divergence-finder">
      <div className="divergence-form">
        <h3>Divergence Finder</h3>
        <p>Compare two sessions to find where they diverged</p>

        <div className="session-selectors">
          <div className="selector-group">
            <label>Session A</label>
            <select
              value={sessionAId}
              onChange={e => setSessionAId(e.target.value)}
            >
              <option value="">Select session A...</option>
              {sessions.map(s => (
                <option key={s.session_id} value={s.session_id}>
                  {s.session_id.substring(0, 8)} - {s.turn_count} turns
                </option>
              ))}
            </select>
          </div>

          <div className="selector-group">
            <label>Session B</label>
            <select
              value={sessionBId}
              onChange={e => setSessionBId(e.target.value)}
            >
              <option value="">Select session B...</option>
              {sessions.map(s => (
                <option key={s.session_id} value={s.session_id}>
                  {s.session_id.substring(0, 8)} - {s.turn_count} turns
                </option>
              ))}
            </select>
          </div>
        </div>

        <button
          onClick={handleFindDivergence}
          disabled={loading || !sessionAId || !sessionBId}
          className="analyze-button"
        >
          {loading ? 'Analyzing...' : 'Find Divergence'}
        </button>
      </div>

      {result && (
        <div className="divergence-result">
          <h4>Divergence Analysis</h4>
          <p className="summary">{result.summary}</p>

          {result.divergence_turn !== null && (
            <div className="divergence-details">
              <h5>Divergence at Turn {result.divergence_turn}</h5>

              {result.message_diff && (
                <div className="message-diff">
                  <div className="diff-section added-in-a">
                    <h6>Only in Session A</h6>
                    <ul>
                      {result.message_diff.added_in_a.map((msg, idx) => (
                        <li key={idx}>{msg}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="diff-section added-in-b">
                    <h6>Only in Session B</h6>
                    <ul>
                      {result.message_diff.added_in_b.map((msg, idx) => (
                        <li key={idx}>{msg}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              {result.similarity_scores && (
                <div className="similarity-chart">
                  <h6>Context Similarity Over Time</h6>
                  <div className="chart-placeholder">
                    {/* Simplified visualization */}
                    {result.similarity_scores.map((score, idx) => (
                      <div
                        key={idx}
                        className="similarity-bar"
                        style={{
                          height: `${score * 100}px`,
                          backgroundColor: score > 0.85 ? '#22c55e' : '#ef4444',
                        }}
                        title={`Turn ${idx}: ${(score * 100).toFixed(1)}%`}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {result.divergence_turn === null && (
            <p className="no-divergence">
              No significant divergence detected. Sessions remained >85% similar throughout.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default DivergenceFinder;
