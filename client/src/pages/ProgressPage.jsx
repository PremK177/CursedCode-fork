import { useState, useEffect } from 'react';
import Header from '../components/Header.jsx';
import Footer from '../components/Footer.jsx';
import GradeBadge from '../components/GradeBadge.jsx';
import { getLearnerProfile } from '../services/api.js';

const MISTAKE_METADATA = {
  off_by_one: {
    title: 'Off-by-one error',
    description: 'Your loop or slice stops one step too early or goes one step too far.'
  },
  unhandled_short_input: {
    title: 'Unhandled short or empty input',
    description: 'Your code breaks or returns an incorrect result on empty lists, short inputs, or when k > len(items).'
  },
  print_not_return: {
    title: 'Printed instead of returned',
    description: 'Your function prints a result to stdout instead of returning it.'
  },
  boundary_comparison: {
    title: 'Boundary comparison error',
    description: 'A strict comparison (< or >) is used where an inclusive comparison (<= or >=) is needed at the boundary.'
  },
  mutates_input: {
    title: 'Mutates input collection',
    description: 'The function modifies an input list in place when the caller expects it to remain unchanged.'
  }
};

const DEFAULT_MASTERY = [
  { concept: 'Lists', score: 0.0, grade: 'Grade 4', difficulty: 'Easy' },
  { concept: 'Loops', score: 0.0, grade: 'Grade 4', difficulty: 'Easy' },
  { concept: 'Strings', score: 0.0, grade: 'Grade 4', difficulty: 'Easy' },
  { concept: 'Slicing', score: 0.0, grade: 'Grade 4', difficulty: 'Easy' },
  { concept: 'Indexing', score: 0.0, grade: 'Grade 4', difficulty: 'Easy' },
  { concept: 'Comparison', score: 0.0, grade: 'Grade 4', difficulty: 'Easy' }
];

export default function ProgressPage({ onNavigate, learnerName, onUpdateLearnerName }) {
  const [masteryData, setMasteryData] = useState(DEFAULT_MASTERY);
  const [nextChallenge, setNextChallenge] = useState({
    challenge_id: 'last-k-total',
    title: 'Last K Total',
    grade: 'Grade 4',
    difficulty: 'Easy',
    reason: 'Start with fundamental sequence slicing and short-input guards to build your diagnostic baseline.'
  });
  const [recurringMistakes, setRecurringMistakes] = useState([]);

  useEffect(() => {
    let active = true;
    getLearnerProfile(learnerName).then((profile) => {
      if (!active || !profile) return;

      if (Array.isArray(profile.mastery) && profile.mastery.length > 0) {
        setMasteryData(
          profile.mastery.map((m) => ({
            concept: m.concept,
            score: m.score !== undefined ? m.score : m.estimate || 0,
            grade: m.grade || 'Grade 4',
            difficulty: m.difficulty || 'Easy'
          }))
        );
      }

      if (profile.next_challenge) {
        setNextChallenge(profile.next_challenge);
      }

      if (Array.isArray(profile.recurring_mistakes)) {
        setRecurringMistakes(profile.recurring_mistakes);
      }
    });

    return () => {
      active = false;
    };
  }, [learnerName]);

  return (
    <div className="page-shell">
      <Header
        currentPath="/progress"
        onNavigate={onNavigate}
        learnerName={learnerName}
        onUpdateLearnerName={onUpdateLearnerName}
      />

      <main className="content-container">
        <div className="page-header-row">
          <div>
            <h1 className="page-heading">Learner Progress &amp; Mastery</h1>
            <p className="page-subheading">
              Diagnostic telemetry for <strong>{learnerName}</strong>. Solving problems without hints grants a higher mastery boost than solving after hints.
            </p>
          </div>
        </div>

        {/* Recommended Next Challenge Card */}
        {nextChallenge && (
          <section className="recommendation-banner" aria-label="Recommended next challenge">
            <div>
              <p className="recommendation-banner__kicker">Recommended Next Problem</p>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
                <h2 className="recommendation-banner__title" style={{ margin: 0 }}>
                  {nextChallenge.title || nextChallenge.challenge_id}
                </h2>
                <GradeBadge
                  grade={nextChallenge.grade || 'Grade 4'}
                  difficulty={nextChallenge.difficulty || 'Easy'}
                  size="sm"
                />
              </div>
              <p className="recommendation-banner__reason">
                <strong>Why this problem:</strong> {nextChallenge.reason}
              </p>
            </div>

            <button
              type="button"
              className="btn-primary"
              onClick={() => onNavigate(`/challenges/${nextChallenge.challenge_id}`)}
            >
              <span>Solve Recommended Problem</span>
              <span aria-hidden="true">→</span>
            </button>
          </section>
        )}

        {/* Recurring Mistake Patterns */}
        <section>
          <div className="section-header-bar">
            <h2 className="section-heading">Recurring Mistake Patterns</h2>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Flagged only when a core mistake appears across 2+ distinct problems
            </span>
          </div>

          <div className="mistakes-panel">
            {recurringMistakes.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {recurringMistakes.map((m) => {
                  const meta = MISTAKE_METADATA[m.category] || {
                    title: m.category,
                    description: `Observed across ${m.challenge_count} different challenges.`
                  };
                  return (
                    <div key={m.category} className="recurring-mistake-card">
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                          <span className="mistake-tag-badge">{m.category}</span>
                          <strong style={{ fontSize: '14px' }}>{meta.title}</strong>
                        </div>
                        <p style={{ margin: '0 0 6px', fontSize: '13px', color: 'var(--text-secondary)' }}>
                          {meta.description}
                        </p>
                        {Array.isArray(m.challenges) && m.challenges.length > 0 && (
                          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', alignItems: 'center' }}>
                            <span style={{ fontSize: '11.5px', color: 'var(--text-muted)' }}>
                              Seen in:
                            </span>
                            {m.challenges.map((slug) => (
                              <button
                                key={slug}
                                type="button"
                                className="topic-pill"
                                onClick={() => onNavigate(`/challenges/${slug}`)}
                              >
                                {slug} ↗
                              </button>
                            ))}
                          </div>
                        )}
                      </div>

                      <span className="core-judge-badge">
                        {m.challenge_count} Challenges
                      </span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '16px 0' }}>
                <h3 style={{ margin: '0 0 6px', fontSize: '15px' }}>No Recurring Mistakes Flagged</h3>
                <p style={{ margin: 0, fontSize: '13px', color: 'var(--text-secondary)' }}>
                  One-off slips on a single problem are isolated so they do not clutter your recurring profile.
                </p>
              </div>
            )}
          </div>
        </section>

        {/* Concept Mastery Grid */}
        <section>
          <div className="section-header-bar">
            <h2 className="section-heading">Concept Mastery Breakdown</h2>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Scale: 0.00 to 1.00
            </span>
          </div>

          <div className="mastery-grid">
            {masteryData.map((item) => (
              <article key={item.concept} className="mastery-dossier-card">
                <div className="mastery-card__header">
                  <h3 className="mastery-card__name">{item.concept}</h3>
                  <GradeBadge grade={item.grade} difficulty={item.difficulty} size="sm" />
                </div>
                <div className="mastery-bar-container">
                  <div
                    className="mastery-bar-fill"
                    style={{ width: `${Math.round(item.score * 100)}%` }}
                    aria-valuenow={Math.round(item.score * 100)}
                    aria-valuemin="0"
                    aria-valuemax="100"
                    role="progressbar"
                  />
                </div>
                <div className="mastery-card__footer">
                  <span>
                    Score: <strong>{item.score.toFixed(2)}</strong> / 1.00
                  </span>
                  <span>{Math.round(item.score * 100)}%</span>
                </div>
              </article>
            ))}
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
