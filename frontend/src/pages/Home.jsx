import React, { useState, useEffect, useMemo } from 'react';
import {
  ArrowRight,
  BookOpen,
  BrainCircuit,
  CheckCircle2,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Sun,
  Sunrise,
  Moon,
  GraduationCap,
  School,
  Edit3,
  Check,
  Quote,
  UserCheck,
  Flame
} from 'lucide-react';

const MODES = [
  {
    id: 'learn',
    eyebrow: 'Build understanding',
    title: 'Learn',
    description: 'Explore new concepts with an AI tutor grounded in your course material and your learning history.',
    action: 'Start a lesson',
    icon: BookOpen,
    tone: 'cyan'
  },
  {
    id: 'revise',
    eyebrow: 'Strengthen recall',
    title: 'Revise',
    description: 'Return to weak areas with focused explanations shaped by your previous attempts and misconceptions.',
    action: 'Review weak areas',
    icon: RefreshCw,
    tone: 'indigo'
  },
  {
    id: 'test',
    eyebrow: 'Prove mastery',
    title: 'Test',
    description: 'Run a focused diagnostic and receive clear, actionable feedback on exactly what to improve next.',
    action: 'Take a diagnostic',
    icon: CheckCircle2,
    tone: 'violet'
  },
];

const MOTIVATIONAL_QUOTES = [
  { text: "The beautiful thing about learning is that no one can take it away from you.", author: "B.B. King" },
  { text: "Every expert was once a beginner. Consistency turns small steps into lasting mastery.", author: "Growth Mindset" },
  { text: "Don’t let what you cannot do interfere with what you can do.", author: "John Wooden" },
  { text: "Mistakes are proof that you are trying and neurons are rewiring for growth.", author: "Cognitive Science" },
  { text: "Focus on progress, not perfection. Today’s effort is tomorrow’s intuition.", author: "Mastery Heuristic" },
  { text: "The mind is not a vessel to be filled, but a fire to be kindled.", author: "Plutarch" },
  { text: "Success is the sum of small efforts repeated day in and day out.", author: "Robert Collier" },
  { text: "Learning is a marathon of curiosity. Take it one concept at a time.", author: "EduNexus Philosophy" },
  { text: "Your potential expands every time you embrace a difficult challenge.", author: "Carol Dweck" },
  { text: "Believe in the process. The real breakthrough happens right after the struggle.", author: "Neuroscience of Learning" },
];

export default function Home({ setMode, studentProfile, onSaveProfile }) {
  // Determine time of day & greeting
  const timeDetails = useMemo(() => {
    const hour = new Date().getHours();
    if (hour >= 5 && hour < 12) {
      return {
        greeting: 'Good morning',
        period: 'morning',
        icon: Sunrise,
        label: 'Morning Focus Edition',
        gradientClass: 'hero--morning',
        accentColor: '#f59e0b',
        glowColor: 'rgba(245, 158, 11, 0.22)',
      };
    } else if (hour >= 12 && hour < 17) {
      return {
        greeting: 'Good afternoon',
        period: 'afternoon',
        icon: Sun,
        label: 'Peak Afternoon Focus',
        gradientClass: 'hero--afternoon',
        accentColor: '#0ea5e9',
        glowColor: 'rgba(14, 165, 233, 0.22)',
      };
    } else {
      return {
        greeting: 'Good night',
        period: 'night',
        icon: Moon,
        label: 'Night Study Session',
        gradientClass: 'hero--night',
        accentColor: '#c084fc',
        glowColor: 'rgba(192, 132, 252, 0.22)',
      };
    }
  }, []);

  // Pick a random motivational quote on every open
  const [quoteIndex, setQuoteIndex] = useState(() =>
    Math.floor(Math.random() * MOTIVATIONAL_QUOTES.length)
  );

  const currentQuote = MOTIVATIONAL_QUOTES[quoteIndex];

  const studentDisplayName = studentProfile?.name?.trim() || '';
  const TimeIcon = timeDetails.icon;

  return (
    <div className="home-page">
      {/* DYNAMIC HERO SECTION WITH TIME-BASED GREETING, MOTIVATION & GRADIENT BACKGROUND */}
      <section
        className={`hero hero--time-adaptive ${timeDetails.gradientClass}`}
        style={{
          position: 'relative',
          padding: '48px 36px',
          borderRadius: '24px',
          border: '1px solid rgba(148, 163, 184, 0.15)',
          overflow: 'hidden',
          marginBottom: '50px',
          boxShadow: `0 24px 70px ${timeDetails.glowColor}`
        }}
      >
        {/* Ambient atmospheric backdrop glow */}
        <div
          style={{
            position: 'absolute',
            top: '-30%',
            right: '-10%',
            width: '500px',
            height: '500px',
            borderRadius: '50%',
            background: timeDetails.glowColor,
            filter: 'blur(90px)',
            opacity: 0.65,
            pointerEvents: 'none',
            zIndex: 0
          }}
        />

        <div className="hero-copy" style={{ position: 'relative', zIndex: 1, maxWidth: '820px' }}>
          {/* Time Badge */}
          <div
            className="eyebrow"
            style={{
              borderColor: `${timeDetails.accentColor}40`,
              background: `${timeDetails.accentColor}18`,
              color: timeDetails.accentColor,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px'
            }}
          >
            <TimeIcon size={15} /> {timeDetails.label}
          </div>

          {/* DYNAMIC GREETING: Good morning/afternoon/night <name of student> */}
          <h1 style={{ margin: '14px 0 16px', lineHeight: 1.15 }}>
            {timeDetails.greeting}
            {studentDisplayName ? (
              <span className="gradient-text">, {studentDisplayName}!</span>
            ) : (
              <span className="gradient-text">!</span>
            )}
          </h1>

          {/* MOTIVATIONAL QUOTE BANNER (Rotates / updates on open) */}
          <div
            style={{
              margin: '18px 0 28px',
              padding: '16px 20px',
              borderRadius: '12px',
              background: 'rgba(15, 27, 44, 0.72)',
              borderLeft: `4px solid ${timeDetails.accentColor}`,
              borderTop: '1px solid rgba(148, 163, 184, 0.12)',
              borderRight: '1px solid rgba(148, 163, 184, 0.12)',
              borderBottom: '1px solid rgba(148, 163, 184, 0.12)',
              backdropFilter: 'blur(12px)',
              maxWidth: '680px'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
              <Quote size={18} style={{ color: timeDetails.accentColor, flexShrink: 0, marginTop: '2px' }} />
              <div>
                <p style={{ fontSize: '0.94rem', color: '#e2e8f0', fontStyle: 'italic', lineHeight: 1.5, margin: 0 }}>
                  "{currentQuote.text}"
                </p>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '8px' }}>
                  <span style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: 650 }}>
                    — {currentQuote.author}
                  </span>
                  <button
                    type="button"
                    onClick={() => setQuoteIndex((prev) => (prev + 1) % MOTIVATIONAL_QUOTES.length)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: timeDetails.accentColor,
                      fontSize: '0.72rem',
                      fontWeight: 650,
                      cursor: 'pointer',
                      padding: 0,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}
                    title="Inspire me with another quote"
                  >
                    <Sparkles size={12} /> New spark
                  </button>
                </div>
              </div>
            </div>
          </div>

          <p className="hero-lead" style={{ marginTop: '0', maxWidth: '640px' }}>
            EduNexus adapts to how you learn—helping you understand concepts, repair knowledge gaps, and build lasting mastery.
          </p>

          {/* Start learning & Check my knowledge buttons */}
          <div className="hero-actions" style={{ marginTop: '26px' }}>
            <button className="btn-primary" onClick={() => setMode('learn')}>
              Start learning <ArrowRight size={17} />
            </button>
            <button className="btn-secondary" onClick={() => setMode('test')}>
              Check my knowledge
            </button>
          </div>

          <div className="trust-row" style={{ marginTop: '24px' }}>
            <span><ShieldCheck size={16} /> Grounded in your material</span>
            <span><BrainCircuit size={16} /> Adapts to your progress</span>
          </div>
        </div>
      </section>

      {/* 3. THREE FOCUSED MODES (Kept unchanged) */}
      <section className="mode-section" aria-labelledby="mode-heading">
        <div className="section-heading">
          <div>
            <span>One workspace, three focused modes</span>
            <h2 id="mode-heading">Choose what you need today</h2>
          </div>
          <p>Each mode shares the same learner profile, so every interaction makes the next one more useful.</p>
        </div>
        <div className="mode-grid">
          {MODES.map(({ id, eyebrow, title, description, action, icon: Icon, tone }, index) => (
            <button
              key={id}
              className={`mode-card mode-card--${tone}`}
              onClick={() => setMode(id)}
              style={{ '--delay': `${index * 90}ms` }}
            >
              <span className="mode-icon"><Icon size={22} /></span>
              <span className="mode-eyebrow">{eyebrow}</span>
              <strong>{title}</strong>
              <span className="mode-description">{description}</span>
              <span className="mode-link">
                {action} <ArrowRight size={16} />
              </span>
            </button>
          ))}
        </div>
      </section>

      {/* 4. ARCHITECTURE STRIP (Kept unchanged) */}
      <section className="architecture-strip">
        <span className="architecture-icon"><BrainCircuit size={22} /></span>
        <div>
          <strong>Built around your learning journey</strong>
          <p>Five specialized agents coordinate retrieval, diagnosis, remediation, and verification through one persistent learner profile.</p>
        </div>
        <span className="architecture-badge">Safe by design</span>
      </section>
    </div>
  );
}

