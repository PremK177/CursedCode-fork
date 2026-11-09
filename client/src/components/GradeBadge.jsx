export default function GradeBadge({ grade, difficulty, showDifficulty = true, size = 'md' }) {
  const diffRaw = (difficulty || '').toLowerCase();
  let tone = 'easy';
  if (diffRaw.includes('hard') || diffRaw.includes('expert') || diffRaw.includes('supreme')) {
    tone = 'hard';
  } else if (diffRaw.includes('med') || diffRaw.includes('adv')) {
    tone = 'medium';
  }

  const label = showDifficulty && difficulty ? difficulty : (grade || 'Easy');
  const secondary = showDifficulty && grade && grade !== difficulty ? grade : null;

  return (
    <span
      className={`grade-badge grade-badge--${size} grade-badge--${tone}`}
      title={secondary ? `${label} (${secondary})` : label}
      aria-label={secondary ? `${label}, ${secondary}` : label}
    >
      <span className="grade-badge__rank">{label}</span>
      {secondary && <span className="grade-badge__diff">· {secondary}</span>}
    </span>
  );
}
