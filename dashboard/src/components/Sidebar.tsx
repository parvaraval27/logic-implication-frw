import React from 'react';

interface SidebarProps {
  benchmarks: string[];
  selectedBenchmark: string;
  onSelect: (b: string) => void;
}

export default function Sidebar({ benchmarks, selectedBenchmark, onSelect }: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h2>Benchmarks</h2>
      </div>
      <div className="sidebar-content">
        {benchmarks.map((b) => (
          <button
            key={b}
            className={`benchmark-btn ${b === selectedBenchmark ? 'active' : ''}`}
            onClick={() => onSelect(b)}
          >
            <div className="benchmark-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="3" width="18" height="18" rx="2" />
                <path d="M9 3v18" />
              </svg>
            </div>
            <span>{b}</span>
          </button>
        ))}
      </div>
    </aside>
  );
}
