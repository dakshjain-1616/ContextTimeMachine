/**
 * FactTracker - Fact presence chart across all turns
 */

import React, { useState } from 'react';
import './FactTracker.css';

function FactTracker({ session }) {
  const [factText, setFactText] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleTrackFact = async () => {
    if (!session || !factText.trim()) return;

    setLoading(true);
    try {
      const response = await fetch(
        `/api/session/${session}/fact`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ fact_text: factText }),
        }
      );
      const data = await response.json();
      setResult(data);
    } catch (err) {
      console.error('Error tracking fact:', err);
    }
    setLoading(false);
  };

  return (
    <div className="fact-tracker">
      <div className="fact-tracker-form">
        <h3>Fact Tracker</h3>
        <p>Enter a fact to track its presence across all turns</p>
        <textarea
          value={factText}
          onChange={e => setFactText(e.target.value)}
          placeholder="e.g., 'The user prefers JSON output'"
          className="fact-input"
        />
        <button
          onClick={handleTrackFact}
          disabled={loading || !session}
          className="track-button"
        >
          {loading ? 'Tracking...' : 'Track Fact'}
        </button>
      </div>

      {result && (
        <div className="fact-result">
          <h4>Results for: "{result.fact_text}"</h4>
          <div className="fact-summary">
            <p>
              First appeared: Turn {result.first_appeared_turn !== null ? result.first_appeared_turn : 'N/A'}
            </p>
            <p>
              Last present: Turn {result.last_present_turn !== null ? result.last_present_turn : 'N/A'}
            </p>
            <p>
              Disappeared: Turn {result.disappeared_at_turn !== null ? result.disappeared_at_turn : 'Still present'}
            </p>
          </div>

          <div className="presence-chart">
            <div className="presence-bar">
              {result.presence_entries.map((entry, idx) => (
                <div
                  key={idx}
                  className={`presence-block ${entry.is_present ? 'present' : 'absent'}`}
                  title={`Turn ${entry.turn}: ${entry.presence_score.toFixed(2)}`}
                  style={{
                    opacity: entry.presence_score,
                  }}
                />
              ))}
            </div>
          </div>

          <div className="presence-legend">
            <span>Green = Present | Red = Absent</span>
          </div>
        </div>
      )}

      {!session && (
        <p className="no-session">Load a session first to track facts</p>
      )}
    </div>
  );
}

export default FactTracker;
