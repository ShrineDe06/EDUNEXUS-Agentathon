import React, { useEffect, useState, useRef } from 'react';
import Navbar from './components/Navbar';
import Home from './pages/Home';
import Learn from './pages/Learn';
import Revise from './pages/Revise';
import Test from './pages/Test';
import Progress from './pages/Progress';
import ProfileModal from './components/ProfileModal';
import MascotAlert from './components/MascotAlert';

export default function App() {
  const [currentMode, setMode] = useState('home');
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);

  // Student Profile state with localStorage persistence
  const [studentProfile, setStudentProfile] = useState(() => {
    try {
      const saved = localStorage.getItem('edunexus_student_profile');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  // Keep studentId synchronized with profile name or fallback
  const [studentId, setStudentId] = useState(() => {
    try {
      const saved = localStorage.getItem('edunexus_student_profile');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed?.name?.trim()) {
          const clean = parsed.name.trim().toLowerCase().replace(/[^a-z0-9_]/g, '_');
          if (clean) return clean;
        }
      }
    } catch {}
    return 'student_1';
  });

  const [learnerSummary, setLearnerSummary] = useState(null);

  // Mascot Alert state for Pomodoro & Hydration
  const [mascotAlert, setMascotAlert] = useState({
    isOpen: false,
    type: 'pomodoro', // 'pomodoro' | 'hydration'
    breakMinutes: 5,
  });

  // Track active study seconds for Pomodoro & Hydration in Learn & Revise only
  const studySecondsRef = useRef(0);
  const hydrationSecondsRef = useRef(0);

  useEffect(() => {
    fetchLearnerSummary();
  }, [studentId]);

  // Pomodoro & Hydration study ticker
  // STRICT RULE: Runs ONLY in 'learn' and 'revise' modes. NEVER in 'test' mode!
  useEffect(() => {
    const isStudyMode = currentMode === 'learn' || currentMode === 'revise';
    if (!isStudyMode) return;

    const interval = setInterval(() => {
      // If an alert is currently showing, don't increment
      if (mascotAlert.isOpen) return;

      const pomodoroConfig = studentProfile?.pomodoro;
      const hydrationConfig = studentProfile?.hydration;

      // 1. Check Pomodoro
      if (pomodoroConfig?.enabled) {
        studySecondsRef.current += 1;
        const targetSeconds = (pomodoroConfig.studyTime || 25) * 60;
        if (studySecondsRef.current >= targetSeconds) {
          studySecondsRef.current = 0; // Reset for after break
          setMascotAlert({
            isOpen: true,
            type: 'pomodoro',
            breakMinutes: pomodoroConfig.breakTime || 5,
          });
          return;
        }
      }

      // 2. Check Hydration & Walk
      if (hydrationConfig?.enabled) {
        hydrationSecondsRef.current += 1;
        const targetHydrationSeconds = (hydrationConfig.interval || 45) * 60;
        if (hydrationSecondsRef.current >= targetHydrationSeconds) {
          hydrationSecondsRef.current = 0;
          setMascotAlert({
            isOpen: true,
            type: 'hydration',
            breakMinutes: 1,
          });
        }
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [currentMode, studentProfile, mascotAlert.isOpen]);

  const fetchLearnerSummary = async () => {
    try {
      const res = await fetch(`/api/learner/${studentId}`);
      if (res.ok) setLearnerSummary(await res.json());
    } catch (err) {
      console.error('Error fetching learner summary:', err);
    }
  };

  const handleSaveStudentProfile = (updatedProfile) => {
    setStudentProfile(updatedProfile);
    try {
      localStorage.setItem('edunexus_student_profile', JSON.stringify(updatedProfile));
    } catch (err) {
      console.error('Error saving profile to localStorage:', err);
    }

    if (updatedProfile?.name?.trim()) {
      const clean = updatedProfile.name.trim().toLowerCase().replace(/[^a-z0-9_]/g, '_');
      if (clean && clean !== studentId) {
        setStudentId(clean);
      }
    }
  };

  const handleAcceptMascotAlert = () => {
    setMascotAlert((prev) => ({ ...prev, isOpen: false }));
    studySecondsRef.current = 0;
  };

  const handleDeclineMascotAlert = () => {
    setMascotAlert((prev) => ({ ...prev, isOpen: false }));
    studySecondsRef.current = 0;
  };

  return (
    <div className="app-shell">
      <Navbar
        currentMode={currentMode}
        setMode={setMode}
        studentId={studentId}
        setStudentId={setStudentId}
        learnerSummary={learnerSummary}
        studentProfile={studentProfile}
        onOpenProfile={() => setIsProfileModalOpen(true)}
      />
      <main className="app-main">
        <div className="page-transition" key={currentMode}>
          {currentMode === 'home' && (
            <Home
              setMode={setMode}
              studentProfile={studentProfile}
              onSaveProfile={handleSaveStudentProfile}
            />
          )}
          {currentMode === 'learn' && (
            <Learn studentId={studentId} onRefreshProfile={fetchLearnerSummary} />
          )}
          {currentMode === 'revise' && (
            <Revise
              studentId={studentId}
              studentProfile={studentProfile}
              onRefreshProfile={fetchLearnerSummary}
            />
          )}
          {currentMode === 'test' && (
            <Test
              studentId={studentId}
              studentProfile={studentProfile}
              onRefreshProfile={fetchLearnerSummary}
            />
          )}
          {currentMode === 'progress' && (
            <Progress
              studentId={studentId}
              studentProfile={studentProfile}
              setMode={setMode}
            />
          )}
        </div>
      </main>

      {/* Profile & Personalisation Modal */}
      <ProfileModal
        isOpen={isProfileModalOpen}
        onClose={() => setIsProfileModalOpen(false)}
        studentProfile={studentProfile}
        onSaveProfile={handleSaveStudentProfile}
      />

      {/* Mascot Alert for Pomodoro Break & Hydration */}
      <MascotAlert
        isOpen={mascotAlert.isOpen}
        type={mascotAlert.type}
        breakMinutes={mascotAlert.breakMinutes}
        onAccept={handleAcceptMascotAlert}
        onDecline={handleDeclineMascotAlert}
      />
    </div>
  );
}

