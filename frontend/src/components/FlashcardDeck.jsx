import React, { useState, useEffect } from 'react';
import { Layers, ChevronLeft, ChevronRight } from 'lucide-react';

export function ConceptVisual({ visual }) {
  if (!visual || visual.type === 'none') return null;
  if (visual.type === 'process') {
    return (
      <div className="flash-process">
        {(visual.steps || []).map((step, index) => (
          <React.Fragment key={`${step}-${index}`}>
            <span>{step}</span>
            {index < visual.steps.length - 1 && <i>→</i>}
          </React.Fragment>
        ))}
      </div>
    );
  }
  const labels = visual.labels || [];
  const values = visual.values || [];
  const maximum = Math.max(...values, 1);
  if (visual.type === 'bar') {
    return (
      <div className="flash-graph">
        <strong>{visual.title}</strong>
        <div className="bar-chart">
          {values.map((value, index) => (
            <div className="bar-item" key={`${labels[index]}-${index}`}>
              <span style={{ height: `${Math.max(8, (value / maximum) * 100)}%` }} />
              <small>{labels[index] || index + 1}</small>
            </div>
          ))}
        </div>
      </div>
    );
  }
  if (visual.type === 'line' && values.length > 1) {
    const points = values.map((value, index) => `${20 + (index * 260) / (values.length - 1)},${112 - (value / maximum) * 88}`).join(' ');
    return (
      <div className="flash-graph">
        <strong>{visual.title}</strong>
        <svg className="line-chart" viewBox="0 0 300 130" role="img" aria-label={visual.title || 'Concept graph'}>
          <line x1="20" y1="112" x2="285" y2="112" />
          <line x1="20" y1="18" x2="20" y2="112" />
          <polyline points={points} />
          {values.map((value, index) => (
            <circle key={index} cx={20 + (index * 260) / (values.length - 1)} cy={112 - (value / maximum) * 88} r="4" />
          ))}
        </svg>
        <div className="line-labels">
          {labels.map((label) => (
            <small key={label}>{label}</small>
          ))}
        </div>
      </div>
    );
  }
  return null;
}

export function InteractiveBlocks({ blocks = [] }) {
  const [openIndex, setOpenIndex] = useState(null);
  if (!blocks.length) return null;
  return (
    <div className="interactive-blocks">
      {blocks.map((block, index) => (
        <button
          type="button"
          key={`${block.label}-${index}`}
          className={`interactive-block interactive-block--${block.kind} ${openIndex === index ? 'is-open' : ''}`}
          onClick={(event) => {
            event.stopPropagation();
            setOpenIndex((current) => current === index ? null : index);
          }}
        >
          <span>
            <b>{block.label}</b>
            <i>{openIndex === index ? '−' : '+'}</i>
          </span>
          {openIndex === index && <p>{block.content}</p>}
        </button>
      ))}
    </div>
  );
}

export default function FlashcardDeck({ data }) {
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const cards = data?.cards || [];

  useEffect(() => {
    setIndex(0);
    setFlipped(false);
  }, [data]);

  if (!cards.length) return null;
  const card = cards[index];

  const move = (direction) => {
    setIndex((current) => (current + direction + cards.length) % cards.length);
    setFlipped(false);
  };

  const flip = () => setFlipped((value) => !value);

  return (
    <div className={`flashcard-deck flashcard-deck--${card.accent || 'cyan'}`}>
      <div className="flashcard-toolbar">
        <span>
          <Layers size={15} /> {data.title || 'Quick Revision Deck'}
        </span>
        <em>{index + 1} / {cards.length}</em>
      </div>
      <div
        className={`flashcard ${flipped ? 'is-flipped' : ''}`}
        onClick={flip}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') flip();
        }}
        role="button"
        tabIndex="0"
        aria-label="Flip flashcard"
      >
        <div className="flashcard-side flashcard-front">
          <small>Concept {index + 1}</small>
          <strong>{card.title}</strong>
          <p>{card.prompt || card.summary}</p>
          <em>Click to reveal key points</em>
        </div>
        <div className="flashcard-side flashcard-back">
          <small>Core Concept</small>
          <strong>{card.summary}</strong>
          <ul>
            {card.points.map((point) => (
              <li key={point}>{point}</li>
            ))}
          </ul>
          <InteractiveBlocks blocks={card.blocks} />
          <ConceptVisual visual={card.visual} />
        </div>
      </div>
      <div className="flashcard-controls">
        <button onClick={() => move(-1)} aria-label="Previous card">
          <ChevronLeft size={17} />
        </button>
        <div>
          {cards.map((item, dotIndex) => (
            <button
              key={item.id || dotIndex}
              className={dotIndex === index ? 'is-active' : ''}
              onClick={() => {
                setIndex(dotIndex);
                setFlipped(false);
              }}
              aria-label={`Open card ${dotIndex + 1}`}
            />
          ))}
        </div>
        <button onClick={() => move(1)} aria-label="Next card">
          <ChevronRight size={17} />
        </button>
      </div>
    </div>
  );
}
