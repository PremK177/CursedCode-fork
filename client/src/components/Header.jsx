import { useState } from 'react';
import { useTheme } from '../context/ThemeContext.jsx';

export default function Header({
  currentPath,
  onNavigate,
  learnerName = 'rohan',
  onUpdateLearnerName,
}) {
  const { isLight, toggleTheme } = useTheme();
  const [editingLearner, setEditingLearner] = useState(false);
  const [draftName, setDraftName] = useState(learnerName);

  const isChallengesActive = currentPath === '/challenges' || currentPath.startsWith('/challenges/');
  const isProgressActive = currentPath === '/progress';
  const isMilestonesActive = currentPath === '/milestones';
  const isImportActive = currentPath === '/import';

  const handleSaveLearner = (e) => {
    e.preventDefault();
    const cleaned = draftName.trim() || 'rohan';
    if (onUpdateLearnerName) {
      onUpdateLearnerName(cleaned);
    } else {
      try {
        localStorage.setItem('cursedcode_learner_name', cleaned);
        window.location.reload();
      } catch {
        // ignore
      }
    }
    setEditingLearner(false);
  };

  return (
    <header className="site-header">
      <div className="site-header__container">
        <button
          type="button"
          className="brand-logo"
          onClick={() => onNavigate('/')}
          aria-label="Debug Dojo Home"
        >
          <span className="brand-logo__mark" aria-hidden="true">&lt;/&gt;</span>
          <span className="brand-logo__wordmark">
            Debug<span className="brand-logo__accent">Dojo</span>
          </span>
        </button>

        <nav className="site-header__nav" aria-label="Primary navigation">
          <button
            type="button"
            className={`nav-link ${isChallengesActive ? 'nav-link--active' : ''}`}
            onClick={() => onNavigate('/challenges')}
            aria-current={isChallengesActive ? 'page' : undefined}
          >
            Problems
          </button>
          <button
            type="button"
            className={`nav-link ${isProgressActive ? 'nav-link--active' : ''}`}
            onClick={() => onNavigate('/progress')}
            aria-current={isProgressActive ? 'page' : undefined}
          >
            Progress
          </button>
          <button
            type="button"
            className={`nav-link ${isImportActive ? 'nav-link--active' : ''}`}
            onClick={() => onNavigate('/import')}
            aria-current={isImportActive ? 'page' : undefined}
          >
            <span>Import Sheets</span>
            <span className="nav-pill-badge">Beta</span>
          </button>
          <button
            type="button"
            className={`nav-link ${isMilestonesActive ? 'nav-link--active' : ''}`}
            onClick={() => onNavigate('/milestones')}
            aria-current={isMilestonesActive ? 'page' : undefined}
          >
            <span>Milestones</span>
            <span className="nav-pill-badge">Beta</span>
          </button>
        </nav>

        <div className="site-header__controls">
          <button
            type="button"
            className="theme-toggle-btn"
            onClick={toggleTheme}
            aria-label={`Switch to ${isLight ? 'dark' : 'light'} theme`}
            title={`Switch to ${isLight ? 'dark' : 'light'} theme`}
          >
            <span className="theme-toggle-icon" aria-hidden="true">{isLight ? '☾' : '☀'}</span>
            <span className="theme-toggle-text">{isLight ? 'Dark' : 'Light'}</span>
          </button>

          {editingLearner ? (
            <form className="learner-inline-form" onSubmit={handleSaveLearner}>
              <input
                type="text"
                className="learner-inline-input"
                value={draftName}
                onChange={(e) => setDraftName(e.target.value)}
                placeholder="learner_id"
                maxLength={24}
                autoFocus
                aria-label="Learner pseudonym"
              />
              <button type="submit" className="learner-inline-save">Save</button>
              <button
                type="button"
                className="learner-inline-cancel"
                onClick={() => {
                  setDraftName(learnerName);
                  setEditingLearner(false);
                }}
              >
                ✕
              </button>
            </form>
          ) : (
            <button
              type="button"
              className="site-header__learner"
              onClick={() => {
                setDraftName(learnerName);
                setEditingLearner(true);
              }}
              title="Click to switch pseudonymous learner ID"
            >
              <span className="learner-dot" aria-hidden="true">●</span>
              <span className="learner-label">Learner:</span>
              <span className="learner-name">{learnerName}</span>
              <span className="learner-edit-hint" aria-hidden="true">✎</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
