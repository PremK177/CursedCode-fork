import { useState, useEffect } from 'react';
import './App.css';
import LandingPage from './pages/LandingPage.jsx';
import ChallengesPage from './pages/ChallengesPage.jsx';
import WorkspacePage from './pages/WorkspacePage.jsx';
import ProgressPage from './pages/ProgressPage.jsx';
import MilestonesPage from './pages/MilestonesPage.jsx';
import ImportSheetPage from './pages/ImportSheetPage.jsx';

export default function App() {
  const [currentPath, setCurrentPath] = useState(window.location.pathname);
  const [learnerName, setLearnerName] = useState(() => {
    try {
      return localStorage.getItem('cursedcode_learner_name') || 'rohan';
    } catch {
      return 'rohan';
    }
  });

  useEffect(() => {
    const handlePopState = () => {
      setCurrentPath(window.location.pathname);
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const navigate = (path) => {
    if (window.location.pathname + window.location.search === path) return;
    window.history.pushState({}, '', path);
    setCurrentPath(window.location.pathname);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const updateLearnerName = (name) => {
    const cleanName = name.trim() || 'rohan';
    setLearnerName(cleanName);
    try {
      localStorage.setItem('cursedcode_learner_name', cleanName);
    } catch {
      // Ignore storage errors in restricted contexts
    }
  };

  if (currentPath === '/') {
    return (
      <LandingPage
        onNavigate={navigate}
        learnerName={learnerName}
        onUpdateLearnerName={updateLearnerName}
      />
    );
  }

  if (currentPath.startsWith('/challenges/')) {
    const challengeId = currentPath.replace('/challenges/', '').split('?')[0];
    return (
      <WorkspacePage
        challengeId={challengeId}
        onNavigate={navigate}
        learnerName={learnerName}
        onUpdateLearnerName={updateLearnerName}
      />
    );
  }

  if (currentPath === '/progress') {
    return (
      <ProgressPage
        onNavigate={navigate}
        learnerName={learnerName}
        onUpdateLearnerName={updateLearnerName}
      />
    );
  }

  if (currentPath === '/milestones') {
    return (
      <MilestonesPage
        onNavigate={navigate}
        learnerName={learnerName}
        onUpdateLearnerName={updateLearnerName}
      />
    );
  }

  if (currentPath === '/import') {
    return (
      <ImportSheetPage
        onNavigate={navigate}
        learnerName={learnerName}
        onUpdateLearnerName={updateLearnerName}
      />
    );
  }

  return (
    <ChallengesPage
      onNavigate={navigate}
      learnerName={learnerName}
      onUpdateLearnerName={updateLearnerName}
    />
  );
}
