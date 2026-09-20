import React, { useEffect, useState, useRef } from 'react';
import { Coffee, Droplets, Check, X } from 'lucide-react';

export default function MascotAlert({
  type, // 'pomodoro' | 'hydration'
  isOpen,
  onAccept,
  onDecline,
  breakMinutes = 5,
}) {
  const [countdown, setCountdown] = useState(10);
  const timerRef = useRef(null);

  useEffect(() => {
    if (!isOpen) {
      if (timerRef.current) clearInterval(timerRef.current);
      setCountdown(10);
      return;
    }

    if (type === 'pomodoro') {
      setCountdown(10);
      timerRef.current = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            clearInterval(timerRef.current);
            if (onAccept) onAccept(); // Auto-press 'Yes' when countdown reaches 0
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isOpen, type, onAccept]);

  if (!isOpen) return null;

  return (
    <div
      className="mascot-alert-overlay"
      style={{
        position: 'fixed',
        bottom: '24px',
        right: '24px',
        zIndex: 10000,
        animation: 'slideUpBounce 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
      }}
    >
      <style>{`
        @keyframes slideUpBounce {
          0% { transform: translateY(50px) scale(0.92); opacity: 0; }
          100% { transform: translateY(0) scale(1); opacity: 1; }
        }
        @keyframes mascotBob {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          50% { transform: translateY(-5px) rotate(2deg); }
        }
        @keyframes clockTickRotate {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        @keyframes pulseGlow {
          0%, 100% { box-shadow: 0 0 15px rgba(45, 212, 191, 0.2); }
          50% { box-shadow: 0 0 25px rgba(45, 212, 191, 0.45); }
        }
      `}</style>

      <div
        style={{
          width: '380px',
          background: 'linear-gradient(145deg, #0d1b2a 0%, #15273d 100%)',
          border: '1px solid rgba(45, 212, 191, 0.35)',
          borderRadius: '16px',
          padding: '18px 20px',
          boxShadow: '0 20px 40px rgba(0,0,0,0.6), 0 0 20px rgba(45, 212, 191, 0.15)',
          color: '#f8fafc',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
          animation: 'pulseGlow 3s infinite ease-in-out',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px' }}>
          {/* Animated Mascot Character */}
          <div
            style={{
              width: '56px',
              height: '56px',
              borderRadius: '14px',
              background: type === 'pomodoro'
                ? 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)'
                : 'linear-gradient(135deg, #0284c7 0%, #06b6d4 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              boxShadow: '0 8px 20px rgba(0,0,0,0.3)',
              animation: 'mascotBob 2.4s ease-in-out infinite',
            }}
          >
            {type === 'pomodoro' ? (
              <svg width="34" height="34" viewBox="0 0 36 36" fill="none">
                {/* Friendly Robot / Owl face */}
                <circle cx="18" cy="18" r="14" fill="#ffedd5" />
                <circle cx="13" cy="16" r="2.5" fill="#ea580c" />
                <circle cx="23" cy="16" r="2.5" fill="#ea580c" />
                <path d="M14 22 C 16 25, 20 25, 22 22" stroke="#ea580c" strokeWidth="2" strokeLinecap="round" />
                <polygon points="18,6 16,11 20,11" fill="#16a34a" />
              </svg>
            ) : (
              <svg width="34" height="34" viewBox="0 0 36 36" fill="none">
                {/* Water droplet mascot */}
                <path d="M18 5 C18 5 9 17 9 23 C9 28 13 32 18 32 C23 32 27 28 27 23 C27 17 18 5 18 5 Z" fill="#e0f2fe" />
                <circle cx="15" cy="22" r="1.8" fill="#0284c7" />
                <circle cx="21" cy="22" r="1.8" fill="#0284c7" />
                <path d="M16 26 C 17 27.5, 19 27.5, 20 26" stroke="#0284c7" strokeWidth="1.6" strokeLinecap="round" />
              </svg>
            )}
          </div>

          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span
                style={{
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                  color: type === 'pomodoro' ? '#fb923c' : '#38bdf8',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '5px'
                }}
              >
                {type === 'pomodoro' ? <Coffee size={13} /> : <Droplets size={13} />}
                {type === 'pomodoro' ? 'EduNexus Study Coach' : 'Hydration & Movement'}
              </span>
            </div>

            <p style={{ margin: '4px 0 0 0', fontSize: '0.88rem', fontWeight: 600, color: '#f1f5f9', lineHeight: 1.35 }}>
              {type === 'pomodoro'
                ? 'Break time is about to start, wanna take a small break?'
                : 'Time to hydrate and stretch! Grab a glass of water and take a quick 1-minute walk 🚶💧'}
            </p>
          </div>
        </div>

        {/* Pomodoro Decision Row with 10s auto-press countdown & animated minimal ticking clock */}
        {type === 'pomodoro' ? (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              paddingTop: '6px',
              borderTop: '1px solid rgba(255, 255, 255, 0.08)',
              marginTop: '4px'
            }}
          >
            {/* Countdown with running clock widget */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                background: 'rgba(255, 255, 255, 0.05)',
                padding: '4px 10px',
                borderRadius: '20px',
                border: '1px solid rgba(255, 255, 255, 0.1)',
              }}
            >
              {/* Minimal Animated Running Clock Widget */}
              <div
                style={{
                  width: '18px',
                  height: '18px',
                  borderRadius: '50%',
                  border: '1.8px solid #38bdf8',
                  position: 'relative',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: 'rgba(56, 189, 248, 0.1)',
                }}
                title="Timer Running"
              >
                {/* Center dot */}
                <div style={{ width: '3px', height: '3px', borderRadius: '50%', background: '#38bdf8' }} />
                {/* Running Clock Hand */}
                <div
                  style={{
                    position: 'absolute',
                    top: '2px',
                    left: '7.5px',
                    width: '1.5px',
                    height: '6.5px',
                    background: '#fbbf24',
                    borderRadius: '1px',
                    transformOrigin: 'bottom center',
                    animation: 'clockTickRotate 1s linear infinite',
                  }}
                />
              </div>

              <span style={{ fontSize: '0.78rem', color: '#cbd5e1', fontWeight: 600 }}>
                Auto Yes in <strong style={{ color: '#fbbf24', fontSize: '0.85rem' }}>{countdown}s</strong>
              </span>
            </div>

            {/* Buttons */}
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                type="button"
                onClick={onDecline}
                style={{
                  padding: '6px 14px',
                  borderRadius: '8px',
                  background: 'rgba(255, 255, 255, 0.08)',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  color: '#94a3b8',
                  fontSize: '0.82rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  transition: 'all 0.15s ease'
                }}
              >
                <X size={14} /> No
              </button>
              <button
                type="button"
                onClick={onAccept}
                style={{
                  padding: '6px 16px',
                  borderRadius: '8px',
                  background: 'linear-gradient(135deg, #14b8a6, #0d9488)',
                  border: 'none',
                  color: '#ffffff',
                  fontSize: '0.82rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  boxShadow: '0 4px 12px rgba(20, 184, 166, 0.35)',
                  transition: 'all 0.15s ease'
                }}
              >
                <Check size={14} /> Yes ({breakMinutes}m)
              </button>
            </div>
          </div>
        ) : (
          <div
            style={{
              display: 'flex',
              justifyContent: 'flex-end',
              paddingTop: '6px',
              borderTop: '1px solid rgba(255, 255, 255, 0.08)',
              marginTop: '4px'
            }}
          >
            <button
              type="button"
              onClick={onAccept}
              style={{
                padding: '6px 16px',
                borderRadius: '8px',
                background: 'linear-gradient(135deg, #0284c7, #0369a1)',
                border: 'none',
                color: '#ffffff',
                fontSize: '0.82rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                boxShadow: '0 4px 12px rgba(2, 132, 199, 0.3)'
              }}
            >
              <Check size={14} /> Got it, refreshed!
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
