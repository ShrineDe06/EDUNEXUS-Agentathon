import React, { useState } from 'react';
import { ArrowRight, BookOpen, Eye, EyeOff, GraduationCap, Loader2, LockKeyhole, UserPlus } from 'lucide-react';

const INITIAL_REGISTER = {
  username: '', password: '', confirmPassword: '', name: '', email: '',
  level: 'College', study: '', year_of_study: '2nd Year', learning_goal: '',
};

export default function Auth({ onAuthenticated }) {
  const [mode, setMode] = useState('login');
  const [login, setLogin] = useState({ username: '', password: '' });
  const [register, setRegister] = useState(INITIAL_REGISTER);
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const switchMode = (nextMode) => { setMode(nextMode); setError(''); setShowPassword(false); };

  const submit = async (event) => {
    event.preventDefault();
    setError('');
    if (mode === 'register' && register.password !== register.confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    setSubmitting(true);
    try {
      const endpoint = mode === 'login' ? '/api/auth/login' : '/api/auth/register';
      const payload = mode === 'login' ? login : {
        username: register.username,
        password: register.password,
        name: register.name,
        email: register.email,
        level: register.level,
        study: register.study,
        year_of_study: register.year_of_study,
        learning_goal: register.learning_goal,
      };
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Authentication failed.');
      onAuthenticated(data.account);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const setRegistration = (field, value) => setRegister((previous) => ({ ...previous, [field]: value }));

  return (
    <main className="auth-page">
      <section className="auth-brand-panel">
        <div className="auth-brand"><span><GraduationCap size={24} /></span><div><strong>EduNexus</strong><small>Adaptive learning workspace</small></div></div>
        <div className="auth-promise">
          <span className="auth-eyebrow"><BookOpen size={14} /> Private learning profile</span>
          <h1>Your learning journey,<br /><em>separated and remembered.</em></h1>
          <p>Every account gets its own local database for chats, uploaded material, revision sessions, tests, schedules, and progress.</p>
        </div>
        <div className="auth-feature-grid">
          <div><strong>Isolated</strong><span>Dedicated local data store</span></div>
          <div><strong>Persistent</strong><span>Continue exactly where you left</span></div>
          <div><strong>Private</strong><span>Passwords are salted and hashed</span></div>
        </div>
      </section>

      <section className="auth-form-panel">
        <div className="auth-card">
          <div className="auth-tabs" role="tablist">
            <button type="button" className={mode === 'login' ? 'is-active' : ''} onClick={() => switchMode('login')}>Sign in</button>
            <button type="button" className={mode === 'register' ? 'is-active' : ''} onClick={() => switchMode('register')}>Create account</button>
          </div>

          <div className="auth-card__heading">
            <span className="auth-card__icon">{mode === 'login' ? <LockKeyhole size={21} /> : <UserPlus size={21} />}</span>
            <div><h2>{mode === 'login' ? 'Welcome back' : 'Create your student account'}</h2><p>{mode === 'login' ? 'Sign in to open your personal workspace.' : 'Set up your login and academic profile in one step.'}</p></div>
          </div>

          {error && <div className="auth-error">{error}</div>}

          <form className="auth-form" onSubmit={submit}>
            {mode === 'register' && (
              <>
                <div className="auth-form-grid">
                  <label><span>Full name</span><input autoFocus required maxLength="100" value={register.name} onChange={(event) => setRegistration('name', event.target.value)} placeholder="Alex Rivera" /></label>
                  <label><span>Email <small>optional</small></span><input type="email" maxLength="160" value={register.email} onChange={(event) => setRegistration('email', event.target.value)} placeholder="alex@example.com" /></label>
                </div>
                <div className="auth-form-grid">
                  <label><span>Education level</span><select value={register.level} onChange={(event) => setRegistration('level', event.target.value)}><option>School</option><option>College</option><option>University</option><option>Professional</option><option>Self-learning</option></select></label>
                  <label><span>Year or stage</span><input maxLength="60" value={register.year_of_study} onChange={(event) => setRegistration('year_of_study', event.target.value)} placeholder="2nd Year" /></label>
                </div>
                <label><span>Course or field of study</span><input maxLength="120" value={register.study} onChange={(event) => setRegistration('study', event.target.value)} placeholder="Computer Science" /></label>
                <label><span>Primary learning goal</span><textarea rows="2" maxLength="500" value={register.learning_goal} onChange={(event) => setRegistration('learning_goal', event.target.value)} placeholder="What would you like EduNexus to help you achieve?" /></label>
              </>
            )}

            <label><span>Username</span><input autoFocus={mode === 'login'} autoComplete="username" required minLength="3" maxLength="32" value={mode === 'login' ? login.username : register.username} onChange={(event) => mode === 'login' ? setLogin((previous) => ({ ...previous, username: event.target.value })) : setRegistration('username', event.target.value)} placeholder="alex_learner" /></label>
            <label><span>Password</span><div className="auth-password"><input type={showPassword ? 'text' : 'password'} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} required minLength={mode === 'register' ? 8 : undefined} value={mode === 'login' ? login.password : register.password} onChange={(event) => mode === 'login' ? setLogin((previous) => ({ ...previous, password: event.target.value })) : setRegistration('password', event.target.value)} placeholder={mode === 'login' ? 'Enter your password' : 'At least 8 characters'} /><button type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? 'Hide password' : 'Show password'}>{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></div></label>
            {mode === 'register' && <label><span>Confirm password</span><input type={showPassword ? 'text' : 'password'} autoComplete="new-password" required minLength="8" value={register.confirmPassword} onChange={(event) => setRegistration('confirmPassword', event.target.value)} placeholder="Enter the password again" /></label>}

            <button className="auth-submit" disabled={submitting}>{submitting ? <><Loader2 className="spin" size={18} /> Please wait…</> : <>{mode === 'login' ? 'Sign in' : 'Create account'} <ArrowRight size={18} /></>}</button>
          </form>
          <p className="auth-local-note">Accounts and learning data are stored locally on this EduNexus installation.</p>
        </div>
      </section>
    </main>
  );
}
