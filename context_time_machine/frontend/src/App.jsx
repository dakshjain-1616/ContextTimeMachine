/**
 * ContextTimeMachine - Interactive post-hoc explorer for LLM agent session context history
 * 🤖 Built with NEO — Powered by NEO MCP for autonomous AI infrastructure development
 */

import React, { useState } from 'react';
import TimelineNavigator from './components/TimelineNavigator';
import ContextPanel from './components/ContextPanel';
import FactTracker from './components/FactTracker';
import DivergenceFinder from './components/DivergenceFinder';
import './App.css';

function App() {
  const [activeMode, setActiveMode] = useState('timeline'); // timeline, fact, divergence
  const [selectedSession, setSelectedSession] = useState(null);
  const [selectedTurn, setSelectedTurn] = useState(0);

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>ContextTimeMachine</h1>
        <p>Interactive context window history explorer</p>
      </header>

      <div className="mode-selector">
        <button
          className={activeMode === 'timeline' ? 'active' : ''}
          onClick={() => setActiveMode('timeline')}
        >
          Timeline Navigator
        </button>
        <button
          className={activeMode === 'fact' ? 'active' : ''}
          onClick={() => setActiveMode('fact')}
        >
          Fact Tracker
        </button>
        <button
          className={activeMode === 'divergence' ? 'active' : ''}
          onClick={() => setActiveMode('divergence')}
        >
          Divergence Finder
        </button>
      </div>

      <div className="content">
        {activeMode === 'timeline' && (
          <div className="timeline-view">
            <TimelineNavigator
              session={selectedSession}
              onTurnSelect={setSelectedTurn}
            />
            <ContextPanel
              session={selectedSession}
              turnNumber={selectedTurn}
            />
          </div>
        )}

        {activeMode === 'fact' && (
          <FactTracker session={selectedSession} />
        )}

        {activeMode === 'divergence' && (
          <DivergenceFinder />
        )}
      </div>
    </div>
  );
}

export default App;
