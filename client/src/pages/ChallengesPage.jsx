import { useState, useMemo, useEffect } from 'react';
import Header from '../components/Header.jsx';
import Footer from '../components/Footer.jsx';
import ChallengeFilters from '../components/ChallengeFilters.jsx';
import ChallengeCard from '../components/ChallengeCard.jsx';
import GradeBadge from '../components/GradeBadge.jsx';
import { CHALLENGES } from '../data/challenges.js';
import { getChallenges } from '../services/api.js';

const CORE_JUDGE_SLUGS = new Set([
  'last-k-total',
  'count-passes',
  'first-n-squares',
  'middle-three'
]);

const STATUS_BADGE = {
  Solved: { icon: '✓', label: 'Solved', cls: 'solved' },
  Attempted: { icon: '●', label: 'Attempted', cls: 'attempted' },
  New: { icon: '○', label: 'Todo', cls: 'new' }
};

export default function ChallengesPage({ onNavigate, learnerName, onUpdateLearnerName }) {
  const initialParams = useMemo(() => {
    const params = new URLSearchParams(window.location.search);
    return {
      q: params.get('q') || '',
      grade: params.get('grade') || 'All grades',
      concept: params.get('concept') || 'All concepts',
      status: params.get('status') || 'All statuses'
    };
  }, []);

  const [searchQuery, setSearchQuery] = useState(initialParams.q);
  const [selectedGrade, setSelectedGrade] = useState(initialParams.grade);
  const [selectedConcept, setSelectedConcept] = useState(initialParams.concept);
  const [selectedStatus, setSelectedStatus] = useState(initialParams.status);
  const [viewMode, setViewMode] = useState('table'); // 'table' | 'cards'
  const [isLoading, setIsLoading] = useState(true);
  const [challenges, setChallenges] = useState(CHALLENGES);
  const [isLive, setIsLive] = useState(false);

  useEffect(() => {
    let active = true;
    getChallenges(learnerName)
      .then((data) => {
        if (active) {
          setChallenges(data);
          setIsLive(true);
          setIsLoading(false);
        }
      })
      .catch(() => {
        if (active) {
          setIsLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [learnerName]);

  useEffect(() => {
    const params = new URLSearchParams();
    if (searchQuery.trim()) params.set('q', searchQuery.trim());
    if (selectedGrade !== 'All grades') params.set('grade', selectedGrade);
    if (selectedConcept !== 'All concepts') params.set('concept', selectedConcept);
    if (selectedStatus !== 'All statuses') params.set('status', selectedStatus);

    const queryString = params.toString();
    const newUrl = queryString ? `/challenges?${queryString}` : '/challenges';
    window.history.replaceState({}, '', newUrl);
  }, [searchQuery, selectedGrade, selectedConcept, selectedStatus]);

  const hasActiveFilters = Boolean(
    searchQuery.trim() ||
    selectedGrade !== 'All grades' ||
    selectedConcept !== 'All concepts' ||
    selectedStatus !== 'All statuses'
  );

  const handleClearFilters = () => {
    setSearchQuery('');
    setSelectedGrade('All grades');
    setSelectedConcept('All concepts');
    setSelectedStatus('All statuses');
  };

  const filteredChallenges = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();

    return challenges.filter((item) => {
      const matchesSearch =
        !query ||
        item.title.toLowerCase().includes(query) ||
        (item.id && item.id.toLowerCase().includes(query)) ||
        (item.description && item.description.toLowerCase().includes(query)) ||
        (item.tags && item.tags.some((tag) => tag.toLowerCase().includes(query)));

      const matchesGrade =
        selectedGrade === 'All grades' || item.grade === selectedGrade;

      const matchesConcept =
        selectedConcept === 'All concepts' || (item.tags && item.tags.includes(selectedConcept));

      const matchesStatus =
        selectedStatus === 'All statuses' || item.status === selectedStatus;

      return matchesSearch && matchesGrade && matchesConcept && matchesStatus;
    });
  }, [challenges, searchQuery, selectedGrade, selectedConcept, selectedStatus]);

  const stats = useMemo(() => {
    const total = challenges.length;
    const solved = challenges.filter((c) => c.status === 'Solved').length;
    const attempted = challenges.filter((c) => c.status === 'Attempted').length;
    const easy = challenges.filter((c) => c.difficulty === 'Easy').length;
    const medium = challenges.filter((c) => c.difficulty === 'Medium').length;
    const hard = challenges.filter((c) => c.difficulty === 'Hard').length;
    return { total, solved, attempted, easy, medium, hard };
  }, [challenges]);

  const handleSelectChallenge = (id) => {
    onNavigate(`/challenges/${id}`);
  };

  return (
    <div className="page-shell">
      <Header
        currentPath="/challenges"
        onNavigate={onNavigate}
        learnerName={learnerName}
        onUpdateLearnerName={onUpdateLearnerName}
      />

      <main className="content-container">
        <div className="page-header-row">
          <div>
            <h1 className="page-heading">Problem Set</h1>
            <p className="page-subheading">
              Debug realistic Python functions, fix edge cases, and pass both visible and hidden test suites.
            </p>
          </div>

          <div className="view-mode-toggle" role="group" aria-label="View mode">
            <button
              type="button"
              className={`view-mode-btn ${viewMode === 'table' ? 'view-mode-btn--active' : ''}`}
              onClick={() => setViewMode('table')}
            >
              Table View
            </button>
            <button
              type="button"
              className={`view-mode-btn ${viewMode === 'cards' ? 'view-mode-btn--active' : ''}`}
              onClick={() => setViewMode('cards')}
            >
              Card Grid
            </button>
          </div>
        </div>

        <section className="stats-strip" aria-label="Problem set summary">
          <div className="stat-card">
            <span className="stat-card__label">Total Problems</span>
            <span className="stat-card__value">{stats.total}</span>
            <span className="stat-card__sub">4 Core Judge · {Math.max(0, stats.total - 4)} Practice</span>
          </div>
          <div className="stat-card">
            <span className="stat-card__label">Solved</span>
            <span className="stat-card__value">{stats.solved} / {stats.total}</span>
            <span className="stat-card__sub">{stats.attempted} in progress</span>
          </div>
          <div className="stat-card">
            <span className="stat-card__label">Difficulty Breakdown</span>
            <span className="stat-card__value">{stats.easy}E · {stats.medium}M · {stats.hard}H</span>
            <span className="stat-card__sub">Grade 4 to Grade 2</span>
          </div>
          <div className="stat-card">
            <span className="stat-card__label">Judge Connection</span>
            <span className="stat-card__value">{isLive ? 'Online' : 'Local'}</span>
            <span className="stat-card__sub">Learner: {learnerName}</span>
          </div>
        </section>

        <ChallengeFilters
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          selectedGrade={selectedGrade}
          onGradeChange={setSelectedGrade}
          selectedConcept={selectedConcept}
          onConceptChange={setSelectedConcept}
          selectedStatus={selectedStatus}
          onStatusChange={setSelectedStatus}
          onClearFilters={handleClearFilters}
          hasActiveFilters={hasActiveFilters}
        />

        <div className="status-bar" aria-live="polite">
          <div>
            Showing <strong>{filteredChallenges.length}</strong> of {challenges.length} problems
          </div>

          <div className="status-bar__active-pills">
            {searchQuery && (
              <button
                type="button"
                className="filter-pill"
                onClick={() => setSearchQuery('')}
              >
                Query: &ldquo;{searchQuery}&rdquo; ✕
              </button>
            )}
            {selectedGrade !== 'All grades' && (
              <button
                type="button"
                className="filter-pill"
                onClick={() => setSelectedGrade('All grades')}
              >
                {selectedGrade} ✕
              </button>
            )}
            {selectedConcept !== 'All concepts' && (
              <button
                type="button"
                className="filter-pill"
                onClick={() => setSelectedConcept('All concepts')}
              >
                {selectedConcept} ✕
              </button>
            )}
            {selectedStatus !== 'All statuses' && (
              <button
                type="button"
                className="filter-pill"
                onClick={() => setSelectedStatus('All statuses')}
              >
                {selectedStatus} ✕
              </button>
            )}
          </div>
        </div>

        {isLoading ? (
          <div className="empty-state" aria-busy="true">
            <p className="empty-state__lead">Loading problem set…</p>
          </div>
        ) : filteredChallenges.length === 0 ? (
          <div className="empty-state">
            <h2 className="empty-state__title">No Matching Problems</h2>
            <p className="empty-state__lead">
              Try adjusting your search query or clearing active filters.
            </p>
            <button
              type="button"
              className="btn-primary"
              onClick={handleClearFilters}
            >
              Reset All Filters
            </button>
          </div>
        ) : viewMode === 'table' ? (
          <div className="problem-table-card">
            <table className="problem-table">
              <thead>
                <tr>
                  <th className="problem-status-cell">Status</th>
                  <th>Problem</th>
                  <th>Topics</th>
                  <th>Difficulty</th>
                  <th>Limit</th>
                  <th style={{ textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredChallenges.map((ch) => {
                  const statusInfo = STATUS_BADGE[ch.status] || STATUS_BADGE.New;
                  const isCoreJudge = CORE_JUDGE_SLUGS.has(ch.id);
                  return (
                    <tr key={ch.id}>
                      <td className="problem-status-cell">
                        <span className={`status-indicator status-indicator--${statusInfo.cls}`}>
                          <span aria-hidden="true">{statusInfo.icon}</span>
                          <span>{statusInfo.label}</span>
                        </span>
                      </td>
                      <td>
                        <button
                          type="button"
                          className="problem-title-btn"
                          onClick={() => handleSelectChallenge(ch.id)}
                        >
                          <span>{ch.title}</span>
                          {isCoreJudge && (
                            <span className="core-judge-badge">Core Judge</span>
                          )}
                        </button>
                        <span className="problem-subtitle">{ch.description}</span>
                      </td>
                      <td>
                        <div className="problem-topics-list">
                          {(ch.tags || []).map((tag) => (
                            <span key={tag} className="topic-pill">
                              {tag}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td>
                        <GradeBadge grade={ch.grade} difficulty={ch.difficulty} size="sm" />
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--text-secondary)' }}>
                        {ch.constraints?.time_limit_ms || ch.time_limit_ms || 500}ms
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <button
                          type="button"
                          className="btn-secondary"
                          onClick={() => handleSelectChallenge(ch.id)}
                        >
                          <span>Solve</span>
                          <span aria-hidden="true">→</span>
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="challenges-grid">
            {filteredChallenges.map((challenge) => (
              <ChallengeCard
                key={challenge.id}
                challenge={challenge}
                onSelect={handleSelectChallenge}
              />
            ))}
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}
