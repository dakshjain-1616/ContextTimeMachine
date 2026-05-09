/**
 * TimelineNavigator - Vertical turn timeline with scrubber
 */

import React, { useEffect, useState } from 'react';
import './TimelineNavigator.css';

function TimelineNavigator({ session, onTurnSelect }) {
  const [turns, setTurns] = useState([]);
  const [selectedTurn, setSelectedTurn] = useState(0);
  const [searchText, setSearchText] = useState('');

  useEffect(() => {
    if (!session) return;

    // Load token profile to get per-turn stats
    fetch(`/api/session/${session}/profile`)
      .then(r => r.json())
      .then(data => {
        setTurns(data.per_turn_stats || []);
      })
      .catch(err => console.error('Error loading profile:', err));
  }, [session]);

  const handleTurnClick = (turnNum) => {
    setSelectedTurn(turnNum);
    onTurnSelect(turnNum);
  };

  const filteredTurns = turns.filter(turn =>
    searchText === '' || turn.turn.toString().includes(searchText)
  );

  return (
    <div className="timeline-navigator">
      <div className="timeline-header">
        <h3>Timeline Navigator</h3>
        <input
          type="text"
          placeholder="Search turns..."
          value={searchText}
          onChange={e => setSearchText(e.target.value)}
          className="search-input"
        />
      </div>

      <div className="turns-list">
        {filteredTurns.map(turn => (
          <div
            key={turn.turn}
            className={`turn-row ${selectedTurn === turn.turn ? 'active' : ''}`}
            onClick={() => handleTurnClick(turn.turn)}
          >
            <span className="turn-number">{turn.turn}</span>
            <div className="token-sparkline">
              {/* Mini bar showing token composition */}
              <div
                className="sparkline-bar"
                style={{
                  background: `linear-gradient(to right,
                    rgba(59, 130, 246, ${turn.system_tokens / turn.total_tokens}),
                    rgba(107, 114, 128, ${turn.history_tokens / turn.total_tokens}),
                    rgba(249, 115, 22, ${turn.tool_results_tokens / turn.total_tokens}),
                    rgba(34, 197, 94, ${turn.current_turn_tokens / turn.total_tokens}))`
                }}
              />
            </div>
            <span className="token-count">{turn.total_tokens} tokens</span>
            {turn.proximity_to_limit > 90 && (
              <span className="eviction-indicator" title="Approaching limit">●</span>
            )}
          </div>
        ))}
      </div>

      {filteredTurns.length === 0 && (
        <p className="no-results">No turns found</p>
      )}
    </div>
  );
}

export default TimelineNavigator;
