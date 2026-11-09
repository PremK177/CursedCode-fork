import { CHALLENGES } from '../data/challenges.js';

const CONFIGURED_API = import.meta.env.VITE_API_URL || '';

/**
 * Resilient fetch helper:
 * 1. Tries configured or relative URL (leveraging Vite dev proxy).
 * 2. If relative request fails due to network error, falls back to direct http://localhost:8000.
 */
async function apiFetch(path, options = {}) {
  const primaryUrl = `${CONFIGURED_API}${path}`;
  try {
    const res = await fetch(primaryUrl, options);
    return res;
  } catch (err) {
    if (!CONFIGURED_API) {
      try {
        return await fetch(`http://localhost:8000${path}`, options);
      } catch {
        // Continue to throw primary error
      }
    }
    throw err;
  }
}

/**
 * Fetch all published challenges from backend, fallback to local dataset on error.
 */
export async function getChallenges(learnerId) {
  let backend = [];
  try {
    const url = learnerId
      ? `/api/challenges?learner_id=${encodeURIComponent(learnerId)}`
      : `/api/challenges`;
    const res = await apiFetch(url);
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    const data = await res.json();
    backend = Array.isArray(data) ? data : [];
  } catch {
    backend = [];
  }

  if (backend.length === 0) return CHALLENGES;

  const byId = new Map(CHALLENGES.map((c) => [c.id, c]));

  return backend.map((b) => {
    const staticChallenge = byId.get(b.slug) || byId.get(b.id);
    if (!staticChallenge) return b;
    return {
      ...staticChallenge,
      ...b,
      id: b.slug || b.id || staticChallenge.id,
      slug: b.slug || staticChallenge.slug,
      title: b.title || staticChallenge.title,
      difficulty: b.difficulty || staticChallenge.difficulty,
      status: b.status || staticChallenge.status,
      tags: Array.isArray(b.tags) && b.tags.length > 0 ? b.tags : staticChallenge.tags,
    };
  });
}

/**
 * Fetch a single challenge by ID/slug from backend, fallback to local dataset.
 */
export async function getChallenge(challengeId) {
  try {
    const res = await apiFetch(`/api/challenges/${encodeURIComponent(challengeId)}`);
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    const b = await res.json();
    const staticChallenge = CHALLENGES.find(
      (c) => c.id === b.slug || c.id === b.id || c.id === challengeId
    );
    if (!staticChallenge) return b;
    return {
      ...staticChallenge,
      ...b,
      id: b.slug || b.id || staticChallenge.id,
      slug: b.slug || staticChallenge.slug,
      starterCode: b.starterCode || b.starter_code || staticChallenge.starterCode,
      visibleTests:
        Array.isArray(b.visibleTests) && b.visibleTests.length > 0
          ? b.visibleTests
          : staticChallenge.visibleTests,
      hiddenTestCount: b.hiddenTestCount || staticChallenge.hiddenTestCount,
    };
  } catch {
    return CHALLENGES.find((c) => c.id === challengeId) || CHALLENGES[0];
  }
}

/**
 * Submit code for execution against visible and hidden tests.
 */
export async function submitCode(learnerId, challengeId, code) {
  const payload = {
    learner_id: learnerId || 'zeroeight',
    challenge_id: challengeId,
    code: code ?? ''
  };

  const res = await apiFetch('/api/submit', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Submission failed (${res.status}): ${errText}`);
  }

  return await res.json();
}

/**
 * Request next progressive hint for a completed submission.
 */
export async function getHint(submissionId, options = {}) {
  const body = {
    submission_id: submissionId,
    ...(options.level ? { level: options.level } : {}),
    ...(options.includePatch ? { include_patch: true } : {}),
  };

  const res = await apiFetch('/api/hint', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(body)
  });

  if (!res.ok) {
    throw new Error(`Hint request failed (${res.status})`);
  }

  return await res.json();
}

/**
 * Fetch learner profile including mastery breakdown, recurring mistakes, and next challenge.
 */
export async function getLearnerProfile(learnerId) {
  try {
    const res = await apiFetch(`/api/learner/${encodeURIComponent(learnerId || 'zeroeight')}`);
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    return await res.json();
  } catch {
    return null;
  }
}

/**
 * Fetch available curated problem sheets (Striver's A2Z, CP-31).
 */
export async function getCuratedSheets() {
  const res = await apiFetch('/api/importer/sheets');
  if (!res.ok) {
    throw new Error(`Failed to load sheets (${res.status})`);
  }
  return await res.json();
}

/**
 * Generate visible test cases and hidden edge cases via OpenRouter.
 */
export async function generateAITestCases(problemData) {
  const res = await apiFetch('/api/importer/generate-tests', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(problemData)
  });
  if (!res.ok) {
    throw new Error(`AI testcase generation failed (${res.status})`);
  }
  return await res.json();
}

/**
 * Import a single problem into the database with test cases and edge cases.
 */
export async function importSingleProblem(problemData) {
  const res = await apiFetch('/api/importer/import-problem', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(problemData)
  });
  if (!res.ok) {
    throw new Error(`Problem import failed (${res.status})`);
  }
  return await res.json();
}

/**
 * Batch import selected problems from a curated sheet with OpenRouter edge cases.
 */
export async function batchImportSheet(sheetId, problemIds = [], autoGenerateTests = true) {
  const res = await apiFetch('/api/importer/batch-import', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      sheet_id: sheetId,
      problem_ids: problemIds,
      auto_generate_tests: autoGenerateTests
    })
  });
  if (!res.ok) {
    throw new Error(`Batch import failed (${res.status})`);
  }
  return await res.json();
}
