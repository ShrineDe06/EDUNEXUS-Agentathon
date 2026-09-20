import React from 'react';

export default function Visualizer({ data }) {
  if (!data || data.type === 'stack_operations') return null;

  const { type, title, explanation } = data;

  return (
    <div style={{
      background: 'rgba(15, 23, 42, 0.95)',
      border: '1px solid rgba(56, 189, 248, 0.3)',
      borderRadius: '14px',
      padding: '20px',
      marginTop: '16px',
      marginBottom: '16px',
      boxShadow: '0 8px 24px rgba(0, 0, 0, 0.4)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
        <h4 style={{ fontSize: '1rem', color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>Concept visualization:</span> {title}
        </h4>
        <span className="badge badge-learning">Interactive</span>
      </div>

      {/* RENDERERS BASED ON TYPE */}
      {type === 'array_indexing' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'center', gap: '8px', marginBottom: '12px' }}>
            {data.elements.map((el, i) => {
              const isHighlighted = data.highlight_slice && i >= data.highlight_slice[0] && i < data.highlight_slice[1];
              return (
                <div key={i} style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginBottom: '4px' }}>
                    idx: {i}
                  </div>
                  <div style={{
                    width: '46px',
                    height: '46px',
                    background: isHighlighted ? 'linear-gradient(135deg, #0284c7, #38bdf8)' : 'rgba(30, 41, 59, 0.9)',
                    border: isHighlighted ? '2px solid #38bdf8' : '1px solid rgba(255, 255, 255, 0.15)',
                    borderRadius: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '1.1rem',
                    fontWeight: 700,
                    color: '#ffffff',
                    boxShadow: isHighlighted ? '0 0 12px rgba(56, 189, 248, 0.5)' : 'none'
                  }}>
                    {el}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: '#818cf8', marginTop: '4px' }}>
                    {data.negative_indices ? data.negative_indices[i] : ''}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {type === 'stack_operations' && (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px' }}>
          <div style={{ fontSize: '0.82rem', color: '#c084fc', fontWeight: 600, marginBottom: '6px' }}>
            Action: {data.operation}
          </div>
          <div style={{
            width: '180px',
            borderLeft: '3px solid #818cf8',
            borderRight: '3px solid #818cf8',
            borderBottom: '3px solid #818cf8',
            borderRadius: '0 0 10px 10px',
            padding: '8px',
            display: 'flex',
            flexDirection: 'column-reverse',
            gap: '6px',
            background: 'rgba(30, 41, 59, 0.5)'
          }}>
            {data.stack.map((item, idx) => (
              <div key={idx} style={{
                background: idx === data.stack.length - 1 ? 'linear-gradient(90deg, #818cf8, #c084fc)' : 'rgba(51, 65, 85, 0.8)',
                padding: '8px',
                borderRadius: '6px',
                textAlign: 'center',
                fontWeight: 600,
                fontSize: '0.9rem',
                color: '#ffffff'
              }}>
                {item} {idx === data.stack.length - 1 ? '(TOP)' : ''}
              </div>
            ))}
          </div>
        </div>
      )}

      {type === 'binary_search' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'center', gap: '6px', flexWrap: 'wrap', marginBottom: '10px' }}>
            {data.array.map((val, idx) => {
              const isMid = idx === data.mid;
              const inRange = idx >= data.low && idx <= data.high;
              return (
                <div key={idx} style={{ textAlign: 'center' }}>
                  <div style={{
                    width: '38px',
                    height: '38px',
                    background: isMid ? '#eab308' : inRange ? 'rgba(56, 189, 248, 0.25)' : 'rgba(30, 41, 59, 0.4)',
                    border: isMid ? '2px solid #fde047' : inRange ? '1px solid #38bdf8' : '1px solid opacity 0.1',
                    borderRadius: '6px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '0.95rem',
                    fontWeight: isMid ? 800 : 500,
                    color: isMid ? '#000000' : '#ffffff'
                  }}>
                    {val}
                  </div>
                  <div style={{ fontSize: '0.68rem', color: isMid ? '#fde047' : '#94a3b8', marginTop: '2px' }}>
                    {isMid ? 'MID' : idx}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {explanation && (
        <div style={{
          marginTop: '12px',
          fontSize: '0.85rem',
          color: '#cbd5e1',
          background: 'rgba(30, 41, 59, 0.6)',
          padding: '10px 14px',
          borderRadius: '8px',
          borderLeft: '3px solid #38bdf8'
        }}>
          Insight: {explanation}
        </div>
      )}
    </div>
  );
}
