import React, { useEffect, useRef, useState } from 'react';
import { GraduationCap } from 'lucide-react';
import Navbar from './components/Navbar';
import Auth from './pages/Auth';
import Home from './pages/Home';
import Learn from './pages/Learn';
import Revise from './pages/Revise';
import Test from './pages/Test';
import Progress from './pages/Progress';
import Admin from './pages/Admin';
import ProfileModal from './components/ProfileModal';
import MascotAlert from './components/MascotAlert';

export default function App() {
  const [currentMode, setMode] = useState('home');
  const [account, setAccount] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [learnerSummary, setLearnerSummary] = useState(null);
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);
  const [mascotAlert, setMascotAlert] = useState({ isOpen: false, type: 'pomodoro', breakMinutes: 5 });
  const studySecondsRef = useRef(0);
  const hydrationSecondsRef = useRef(0);

  const studentId = account?.id || '';
  const studentProfile = account?.profile || null;
  // `admin` is the reserved local teacher account. The username fallback also
  // handles a session restored from a backend process started before roles were migrated.
  const isAdmin = account?.role === 'admin' || account?.username?.toLowerCase() === 'admin';

  useEffect(() => {
    const theme = studentProfile?.theme || localStorage.getItem('edunexus:theme') || 'nexus';
    document.documentElement.dataset.theme = theme;
    localStorage.setItem('edunexus:theme', theme);
  }, [studentProfile?.theme]);

  useEffect(() => {
    fetch('/api/auth/me')
      .then(async (response) => response.ok ? response.json() : null)
      .then((data) => setAccount(data?.account || null))
      .catch(() => setAccount(null))
      .finally(() => setAuthLoading(false));
  }, []);

  useEffect(() => {
    if (studentId && !isAdmin) fetchLearnerSummary();
    else setLearnerSummary(null);
  }, [studentId, isAdmin]);

  useEffect(() => {
    const isStudyMode = currentMode === 'learn' || currentMode === 'revise';
    if (!isStudyMode || !account) return;
    const interval = setInterval(() => {
      if (mascotAlert.isOpen) return;
      const pomodoro = studentProfile?.pomodoro;
      const hydration = studentProfile?.hydration;
      if (pomodoro?.enabled) {
        studySecondsRef.current += 1;
        if (studySecondsRef.current >= (pomodoro.studyTime || 25) * 60) {
          studySecondsRef.current = 0;
          setMascotAlert({ isOpen: true, type: 'pomodoro', breakMinutes: pomodoro.breakTime || 5 });
          return;
        }
      }
      if (hydration?.enabled) {
        hydrationSecondsRef.current += 1;
        if (hydrationSecondsRef.current >= (hydration.interval || 45) * 60) {
          hydrationSecondsRef.current = 0;
          setMascotAlert({ isOpen: true, type: 'hydration', breakMinutes: 1 });
        }
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [currentMode, studentProfile, mascotAlert.isOpen, account]);

  const fetchLearnerSummary = async () => {
    if (!studentId) return;
    try {
      const response = await fetch(`/api/learner/${studentId}`);
      if (response.status === 401) { setAccount(null); return; }
      if (response.ok) setLearnerSummary(await response.json());
    } catch (error) {
      console.error('Error fetching learner summary:', error);
    }
  };

  const handleSaveStudentProfile = async (updatedProfile) => {
    const previousTheme = studentProfile?.theme || 'nexus';
    const nextTheme = updatedProfile.theme || 'nexus';
    document.documentElement.dataset.theme = nextTheme;
    localStorage.setItem('edunexus:theme', nextTheme);
    try {
      const response = await fetch('/api/auth/profile', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile: updatedProfile }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Could not save profile.');
      setAccount(data.account);
    } catch (error) {
      document.documentElement.dataset.theme = previousTheme;
      localStorage.setItem('edunexus:theme', previousTheme);
      throw error;
    }
  };

  const handleLogout = async () => {
    await fetch('/api/auth/logout', { method: 'POST' }).catch(() => null);
    setAccount(null);
    document.documentElement.dataset.theme = 'nexus';
    localStorage.removeItem('edunexus:theme');
    setLearnerSummary(null);
    setMode('home');
  };

  const closeMascot = () => {
    setMascotAlert((previous) => ({ ...previous, isOpen: false }));
    studySecondsRef.current = 0;
  };

  if (authLoading) return <div className="auth-loading"><span className="brand-mark"><GraduationCap size={21} /></span><div className="generation-skeleton"><i /><i /><i /></div><strong>Opening EduNexus…</strong></div>;
  if (!account) return <Auth onAuthenticated={setAccount} />;
  if (isAdmin) return <Admin account={account} onLogout={handleLogout} />;

  return (
    <div className="app-shell">
      <Navbar currentMode={currentMode} setMode={setMode} learnerSummary={learnerSummary} studentProfile={studentProfile} username={account.username} onOpenProfile={() => setIsProfileModalOpen(true)} onLogout={handleLogout} />
      <main className="app-main"><div className="page-transition" key={currentMode}>
        {currentMode === 'home' && <Home setMode={setMode} studentProfile={studentProfile} onSaveProfile={handleSaveStudentProfile} />}
        {currentMode === 'learn' && <Learn studentId={studentId} onRefreshProfile={fetchLearnerSummary} />}
        {currentMode === 'revise' && <Revise studentId={studentId} studentProfile={studentProfile} onRefreshProfile={fetchLearnerSummary} />}
        {currentMode === 'test' && <Test studentId={studentId} studentProfile={studentProfile} onRefreshProfile={fetchLearnerSummary} />}
        {currentMode === 'progress' && <Progress studentId={studentId} studentProfile={studentProfile} setMode={setMode} />}
      </div></main>
      <ProfileModal isOpen={isProfileModalOpen} onClose={() => setIsProfileModalOpen(false)} studentProfile={studentProfile} onSaveProfile={handleSaveStudentProfile} />
      <MascotAlert isOpen={mascotAlert.isOpen} type={mascotAlert.type} breakMinutes={mascotAlert.breakMinutes} onAccept={closeMascot} onDecline={closeMascot} />
    </div>
  );
}
