import GradeBadge from './GradeBadge.jsx';

const STATUS_MAP = {
  Solved: { icon: '✓', label: 'Solved', cls: 'solved' },
  Attempted: { icon: '●', label: 'Attempted', cls: 'attempted' },
  New: { icon: '○', label: 'Todo', cls: 'new' }
};

export default function ChallengeCard({ challenge, onSelect }) {
  const { id, title, description, grade, difficulty, tags = [], status, estimatedTime, constraints } = challenge;
  const statusInfo = STATUS_MAP[status] || STATUS_MAP.New;

  return (
    <article className="challenge-card">
      <div className="challenge-card__top">
        <GradeBadge grade={grade} difficulty={difficulty} />
        <div className="challenge-card__meta">
          {constraints?.time_limit_ms ? (
            <span title="Time limit per test case">{constraints.time_limit_ms}ms</span>
          ) : (
            estimatedTime && <span>{estimatedTime}</span>
          )}
          <span className={`status-indicator status-indicator--${statusInfo.cls}`}>
            <span aria-hidden="true">{statusInfo.icon}</span>
            <span>{statusInfo.label}</span>
          </span>
        </div>
      </div>

      <div>
        <h2 className="challenge-card__title">{title}</h2>
        <p className="challenge-card__desc">{description}</p>
      </div>

      <div className="challenge-card__tags" aria-label="Topics">
        {tags.map((tag) => (
          <span key={tag} className="topic-pill">
            {tag}
          </span>
        ))}
      </div>

      <button
        type="button"
        className="challenge-card__enter-btn"
        onClick={() => onSelect(id)}
      >
        <span>Solve Problem</span>
        <span aria-hidden="true">→</span>
      </button>
    </article>
  );
}
