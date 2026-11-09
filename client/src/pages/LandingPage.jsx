import { useState } from 'react';
import Header from '../components/Header.jsx';
import Footer from '../components/Footer.jsx';

const SAMPLE_BUGGY_CODE = `def last_k_total(marks, k):
    total = 0
    for i in range(len(marks) - k, len(marks)):
        total += marks[i]
    return total`;

export default function LandingPage({ onNavigate, learnerName, onUpdateLearnerName }) {
  const [inputName, setInputName] = useState(learnerName || 'rohan');

  const handleSubmit = (e) => {
    e.preventDefault();
    const finalName = inputName.trim() || 'rohan';
    if (onUpdateLearnerName) {
      onUpdateLearnerName(finalName);
    }
    onNavigate('/challenges');
  };

  return (
    <div className="landing-layout">
      <Header
        currentPath="/"
        onNavigate={onNavigate}
        learnerName={learnerName}
        onUpdateLearnerName={onUpdateLearnerName}
      />

      <main className="landing-main">
        <div>
          <div className="landing-kicker">
            <span>●</span>
            <span>Interactive Python Debugging &amp; Mastery Platform</span>
          </div>

          <h1 className="landing-title">
            Master edge cases, boundary conditions, and Python debugging.
          </h1>

          <p className="landing-lead">
            Practice on realistic buggy code and algorithmic challenges. Run against visible and hidden edge-case suites inside an isolated sandbox, track recurring mistake patterns, and unlock progressive hints without giving away the answer.
          </p>

          <div className="landing-start-card">
            <h2 className="landing-start-card__title">Start or Resume a Learner Session</h2>
            <form className="landing-form-row" onSubmit={handleSubmit}>
              <div className="landing-input-wrap">
                <span className="landing-input-prefix" aria-hidden="true">learner:</span>
                <input
                  id="learner-input"
                  type="text"
                  className="landing-input"
                  value={inputName}
                  onChange={(e) => setInputName(e.target.value)}
                  placeholder="e.g. rohan"
                  maxLength={24}
                  autoComplete="off"
                  aria-label="Learner pseudonym"
                />
              </div>

              <button type="submit" className="btn-primary">
                <span>Open Problem Set</span>
                <span aria-hidden="true">→</span>
              </button>
            </form>
            <p className="landing-start-card__hint">
              Your submissions, recurring mistakes, and concept mastery are tracked per learner ID.
            </p>
          </div>

          <div className="landing-features">
            <div className="landing-feature-card">
              <h3 className="landing-feature-card__title">1. Isolated Sandbox</h3>
              <p className="landing-feature-card__desc">
                Every submission runs with strict time, memory, output, and filesystem limits.
              </p>
            </div>
            <div className="landing-feature-card">
              <h3 className="landing-feature-card__title">2. Hidden Edge Cases</h3>
              <p className="landing-feature-card__desc">
                See full inputs on visible tests and pass/fail verdicts on hidden boundary tests.
              </p>
            </div>
            <div className="landing-feature-card">
              <h3 className="landing-feature-card__title">3. 4-Step Progressive Hints</h3>
              <p className="landing-feature-card__desc">
                Nudge → concrete trace → failure concept → structural fix, never leaking raw code.
              </p>
            </div>
          </div>
        </div>

        <aside className="landing-preview-card" aria-label="Debugging preview">
          <div className="landing-preview-card__bar">
            <span className="landing-preview-dots" aria-hidden="true"><i /><i /><i /></span>
            <span>last-k-total · solution.py</span>
            <span>Python 3</span>
          </div>
          <pre className="landing-preview-code">
            <code>{SAMPLE_BUGGY_CODE}</code>
          </pre>
          <div className="landing-preview-diagnostics">
            <div className="landing-preview-row">
              <span>Visible Tests (1–2)</span>
              <span className="status-indicator status-indicator--solved">✓ 2 / 2 Passed</span>
            </div>
            <div className="landing-preview-row">
              <span>Hidden Edge Cases (1–3)</span>
              <span className="status-indicator status-indicator--attempted">✕ 1 Passed · 2 Wrong output</span>
            </div>
            <div className="landing-preview-row">
              <span>Detected Pattern</span>
              <span className="mistake-tag-badge">unhandled_short_input</span>
            </div>
          </div>
        </aside>
      </main>

      <Footer />
    </div>
  );
}
