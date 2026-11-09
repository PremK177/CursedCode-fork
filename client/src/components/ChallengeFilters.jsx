import { CONCEPTS, GRADE_SCALE, STATUSES } from '../data/challenges.js';

export default function ChallengeFilters({
  searchQuery,
  onSearchChange,
  selectedGrade,
  onGradeChange,
  selectedConcept,
  onConceptChange,
  selectedStatus,
  onStatusChange,
  onClearFilters,
  hasActiveFilters
}) {
  return (
    <section className="filters-bar" aria-label="Filter problems">
      <div className="filters-grid">
        <div className="filter-group">
          <label htmlFor="challenge-search" className="filter-label">
            Search Problems
          </label>
          <div className="search-input-wrapper">
            <span className="search-icon" aria-hidden="true">⌕</span>
            <input
              id="challenge-search"
              type="text"
              className="filter-input filter-input--search"
              placeholder="Search by problem title, slug, or topic..."
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
            />
            {searchQuery && (
              <button
                type="button"
                className="clear-search-btn"
                onClick={() => onSearchChange('')}
                aria-label="Clear search input"
              >
                ✕
              </button>
            )}
          </div>
        </div>

        <div className="filter-group">
          <label htmlFor="grade-filter" className="filter-label">
            Difficulty
          </label>
          <select
            id="grade-filter"
            className="filter-select"
            value={selectedGrade}
            onChange={(e) => onGradeChange(e.target.value)}
          >
            <option value="All grades">All Difficulties</option>
            {GRADE_SCALE.slice(0, 3).map((item) => (
              <option key={item.grade} value={item.grade}>
                {item.difficulty} ({item.grade})
              </option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="concept-filter" className="filter-label">
            Topic
          </label>
          <select
            id="concept-filter"
            className="filter-select"
            value={selectedConcept}
            onChange={(e) => onConceptChange(e.target.value)}
          >
            <option value="All concepts">All Topics</option>
            {CONCEPTS.map((concept) => (
              <option key={concept} value={concept}>
                {concept}
              </option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="status-filter" className="filter-label">
            Status
          </label>
          <select
            id="status-filter"
            className="filter-select"
            value={selectedStatus}
            onChange={(e) => onStatusChange(e.target.value)}
          >
            <option value="All statuses">All Statuses</option>
            {STATUSES.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <button
            type="button"
            className="reset-filters-btn"
            onClick={onClearFilters}
            disabled={!hasActiveFilters}
          >
            <span aria-hidden="true">↺</span>
            <span>Reset</span>
          </button>
        </div>
      </div>
    </section>
  );
}
