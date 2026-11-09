import { useState, useEffect, useRef } from 'react';
import Header from '../components/Header.jsx';
import GradeBadge from '../components/GradeBadge.jsx';
import { CHALLENGES } from '../data/challenges.js';
import { getChallenge, submitCode, getHint } from '../services/api.js';
import botAvatarImg from '../assets/hint_bot.webp';

const HINT_STEP_TITLES = {
  1: 'Step 1 · Where to Look',
  2: 'Step 2 · Concrete Case to Trace',
  3: 'Step 3 · Failure Mechanism',
  4: 'Step 4 · Structural Fix'
};

function formatOutcome(outcome) {
  switch (outcome) {
    case 'passed':
      return 'Passed';
    case 'wrong_output':
      return 'Wrong output';
    case 'runtime_error':
      return 'Runtime error';
    case 'timeout':
      return 'Timeout';
    default:
      return 'Not run';
  }
}

function getOutcomeIcon(outcome) {
  switch (outcome) {
    case 'passed':
      return '✓';
    case 'wrong_output':
      return '✕';
    case 'runtime_error':
      return '!';
    case 'timeout':
      return '⏱';
    default:
      return '○';
  }
}

function detectSuspectLine(codeText, mistakeTags = [], visibleResults = [], explanation = '') {
  const lines = (codeText || '').split('\n');
  if (lines.length <= 1) return 1;

  const lineMatch = (explanation || '').match(/line\s+(\d+)/i);
  if (lineMatch) {
    const parsed = parseInt(lineMatch[1], 10);
    if (!isNaN(parsed) && parsed >= 1 && parsed <= lines.length) {
      return parsed;
    }
  }

  if (mistakeTags.includes('print_not_return')) {
    const printIdx = lines.findIndex((l) => /print\s*\(/.test(l));
    if (printIdx !== -1) return printIdx + 1;
  }

  if (mistakeTags.includes('mutates_input')) {
    const mutIdx = lines.findIndex((l) => /\.(sort|append|extend|insert|remove|pop|clear|reverse)\s*\(|del\s+/.test(l));
    if (mutIdx !== -1) return mutIdx + 1;
  }

  if (mistakeTags.includes('unhandled_short_input')) {
    const sliceIdx = lines.findIndex((l) => /\[.*\]|range\s*\(/.test(l) && !l.trim().startsWith('def '));
    if (sliceIdx !== -1) return sliceIdx + 1;
  }

  if (mistakeTags.includes('boundary_comparison') || mistakeTags.includes('off_by_one')) {
    const loopOrCompIdx = lines.findIndex((l) => /(for|while|if|return)\s+.*(range|<=|>=|<|>|==|:)/.test(l));
    if (loopOrCompIdx !== -1) return loopOrCompIdx + 1;
  }

  const returnIdx = lines.findIndex((l) => /^\s*return\b/.test(l));
  if (returnIdx !== -1) return returnIdx + 1;

  return lines.length > 1 ? 2 : 1;
}

function getNaturalLanguageDiagnostic({ mistakeTags, visibleResults, explanation, targetLine, codeText }) {
  const lines = (codeText || '').split('\n');
  const codeLine = lines[targetLine - 1] || '';
  const failedTest = (visibleResults || []).find((r) => r.outcome && r.outcome !== 'passed');

  if (failedTest?.outcome === 'runtime_error') {
    return {
      title: 'Runtime Error',
      detail: explanation || 'A runtime error occurred while executing this block. Check indices, variable names, and edge inputs.',
      lineSnippet: codeLine
    };
  }

  if (failedTest?.outcome === 'timeout') {
    return {
      title: 'Time Limit Exceeded',
      detail: explanation || 'Execution timed out. Check if a loop condition fails to progress toward termination.',
      lineSnippet: codeLine
    };
  }

  if (mistakeTags.includes('print_not_return')) {
    return {
      title: 'Printed Instead of Returned',
      detail: 'Your function prints output instead of returning it. Return the computed value so the test harness can verify it.',
      lineSnippet: codeLine
    };
  }

  if (mistakeTags.includes('mutates_input')) {
    return {
      title: 'Input Collection Mutated',
      detail: 'This line modifies the caller\'s input list in place. Operate on a copy or use a non-mutating expression.',
      lineSnippet: codeLine
    };
  }

  if (mistakeTags.includes('unhandled_short_input')) {
    return {
      title: 'Unhandled Short / Empty Input',
      detail: explanation || 'Check what happens when the input list is empty, shorter than expected, or when k exceeds len(items).',
      lineSnippet: codeLine
    };
  }

  if (mistakeTags.includes('boundary_comparison') || mistakeTags.includes('off_by_one')) {
    return {
      title: 'Boundary / Off-By-One Check',
      detail: explanation || 'Verify whether your loop range, slice stop index, or comparison operator (< vs <=) is off by one at the boundary.',
      lineSnippet: codeLine
    };
  }

  return {
    title: 'Logic Discrepancy',
    detail: explanation || 'Re-check how this line updates or returns the result across edge-case inputs.',
    lineSnippet: codeLine
  };
}

export default function WorkspacePage({ challengeId, onNavigate, learnerName, onUpdateLearnerName }) {
  const initialChallenge = CHALLENGES.find((c) => c.id === challengeId) || CHALLENGES[0];
  const [challenge, setChallenge] = useState(initialChallenge);
  const [starterCode, setStarterCode] = useState(initialChallenge.starterCode || '');
  const [code, setCode] = useState(initialChallenge.starterCode || '');
  const [sandboxStatus, setSandboxStatus] = useState('Sandbox ready');
  const [hasRun, setHasRun] = useState(false);
  const [isRunning, setIsRunning] = useState(false);

  const [leftTab, setLeftTab] = useState('description'); // 'description' | 'coach'
  const [selectedCaseIndex, setSelectedCaseIndex] = useState(0);
  const [consoleTab, setConsoleTab] = useState('testcase'); // 'testcase' | 'result'
  const [explanation, setExplanation] = useState('');
  const [mistakeTags, setMistakeTags] = useState([]);
  const [limitHit, setLimitHit] = useState(null);

  const [submissionId, setSubmissionId] = useState(null);
  const [visibleResults, setVisibleResults] = useState([]);
  const [hiddenResults, setHiddenResults] = useState([]);

  const [revealedHints, setRevealedHints] = useState([]);
  const [isFetchingHint, setIsFetchingHint] = useState(false);
  const [remainingHints, setRemainingHints] = useState(4);
  const [patchApplied, setPatchApplied] = useState(false);

  const [activeLine, setActiveLine] = useState(1);
  const [targetLine, setTargetLine] = useState(1);
  const [botActive, setBotActive] = useState(false);
  const [botMode, setBotMode] = useState('hint'); // 'hint' | 'error'
  const [scrollTop, setScrollTop] = useState(0);

  const textareaRef = useRef(null);
  const gutterRef = useRef(null);

  useEffect(() => {
    let active = true;
    getChallenge(challengeId).then((data) => {
      if (active && data) {
        setChallenge(data);
        const starter = data.starterCode || data.starter_code || '';
        setStarterCode(starter);
        setCode(starter);
        setHasRun(false);
        setLeftTab('description');
        setConsoleTab('testcase');
        setSubmissionId(null);
        setVisibleResults([]);
        setHiddenResults([]);
        setRevealedHints([]);
        setRemainingHints(4);
        setPatchApplied(false);
        setBotActive(false);
        setActiveLine(1);
        setTargetLine(1);
        setScrollTop(0);
        setSandboxStatus('Sandbox ready');
        setSelectedCaseIndex(0);
        setExplanation('');
        setMistakeTags([]);
        setLimitHit(null);
      }
    });
    return () => {
      active = false;
    };
  }, [challengeId]);

  const handleRun = async () => {
    if (isRunning) return;
    setIsRunning(true);
    setPatchApplied(false);
    setSandboxStatus('Running in sandbox…');

    try {
      const res = await submitCode(learnerName, challenge.id, code);
      setSubmissionId(res.submission_id);
      setVisibleResults(res.visible || []);
      setHiddenResults(res.hidden || []);
      setExplanation(res.explanation || '');
      setMistakeTags(res.mistake_tags || []);
      setLimitHit(res.limit || null);
      setHasRun(true);
      setConsoleTab('result');

      const allVisPass = (res.visible || []).every((r) => r.outcome === 'passed');
      const allHidPass = (res.hidden || []).every((r) => r.outcome === 'passed');
      if (!allVisPass || !allHidPass) {
        setLeftTab('coach');
      }

      if (res.limit) {
        setSandboxStatus(`Limit reached: ${res.limit}`);
      } else {
        setSandboxStatus('Execution complete');
      }
    } catch {
      setSandboxStatus('Execution error — please retry');
    } finally {
      setIsRunning(false);
    }
  };

  const handleGetHint = async (options = {}) => {
    if (isFetchingHint) return;
    setIsFetchingHint(true);
    setLeftTab('coach');

    try {
      let currentSubId = submissionId;
      if (!currentSubId) {
        setSandboxStatus('Evaluating code for hints…');
        const submitRes = await submitCode(learnerName, challenge.id, code);
        currentSubId = submitRes.submission_id;
        setSubmissionId(currentSubId);
        setVisibleResults(submitRes.visible || []);
        setHiddenResults(submitRes.hidden || []);
        setExplanation(submitRes.explanation || '');
        setMistakeTags(submitRes.mistake_tags || []);
        setLimitHit(submitRes.limit || null);
        setHasRun(true);
        setConsoleTab('result');
        setSandboxStatus('Code evaluated');
      }

      const res = await getHint(currentSubId, options);
      setRevealedHints((prev) => {
        const existingIdx = prev.findIndex((h) => h.index === res.hint_index);
        if (existingIdx !== -1) {
          const updated = [...prev];
          updated[existingIdx] = {
            index: res.hint_index,
            text: res.hint,
            code_patch: res.code_patch || updated[existingIdx].code_patch
          };
          return updated;
        }
        return [...prev, { index: res.hint_index, text: res.hint, code_patch: res.code_patch }];
      });
      if (res.code_patch) {
        setPatchApplied(false);
      }
      if (res.remaining !== undefined) {
        setRemainingHints(res.remaining);
      } else {
        setRemainingHints((prev) => Math.max(0, prev - 1));
      }
    } catch {
      setSandboxStatus('Could not fetch hint');
    } finally {
      setIsFetchingHint(false);
    }
  };

  const handleApplyCodePatch = (patch) => {
    if (!patch) return;
    const patched =
      patch.patched_code ||
      code
        .split('\n')
        .map((line, idx) => (idx + 1 === patch.target_line ? patch.replacement_snippet : line))
        .join('\n');
    setCode(patched);
    if (patch.target_line) {
      setTargetLine(patch.target_line);
    }
    setPatchApplied(true);
  };

  const handleResetCode = () => {
    setCode(starterCode);
    setBotActive(false);
    setPatchApplied(false);
  };

  const visibleTotal = visibleResults.length || (challenge.visibleTests ? challenge.visibleTests.length : 0);
  const visiblePassed = visibleResults.filter((r) => r.outcome === 'passed').length;
  const hiddenTotal = hiddenResults.length || (challenge.hiddenTestCount || 3);
  const hiddenPassed = hiddenResults.filter((r) => r.outcome === 'passed').length;
  const allPassed = hasRun && visiblePassed === visibleTotal && hiddenPassed === hiddenTotal;
  const hasFailedTests = hasRun && !allPassed;

  const suspectErrorLine = detectSuspectLine(code, mistakeTags, visibleResults, explanation);
  const botDiagnostic = getNaturalLanguageDiagnostic({
    mistakeTags,
    visibleResults,
    explanation,
    targetLine,
    codeText: code
  });

  const latestHint = revealedHints.length > 0 ? revealedHints[revealedHints.length - 1] : null;
  const codeLines = code.split('\n');

  const handleDeployBot = (forcedMode) => {
    const mode = forcedMode || (hasFailedTests ? 'error' : 'hint');
    setBotMode(mode);

    let target = 1;
    if (mode === 'error') {
      target = suspectErrorLine;
    } else {
      target = activeLine || (codeLines.length > 1 ? 2 : 1);
      if (revealedHints.length === 0 && !isFetchingHint) {
        handleGetHint();
      }
    }

    setTargetLine(target);
    setBotActive(true);

    if (textareaRef.current) {
      const targetScrollTop = Math.max(0, (target - 1) * 24 - 80);
      textareaRef.current.scrollTo({ top: targetScrollTop, behavior: 'smooth' });
    }
  };

  const handleCursorChange = (e) => {
    const el = e.target;
    const pos = el.selectionStart || 0;
    const linesBefore = el.value.substring(0, pos).split('\n');
    setActiveLine(Math.max(1, linesBefore.length));
  };

  const handleKeyDown = (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      handleRun();
      return;
    }
    if (e.key === 'Tab') {
      e.preventDefault();
      const el = e.target;
      const start = el.selectionStart;
      const end = el.selectionEnd;
      const nextVal = code.substring(0, start) + '    ' + code.substring(end);
      setCode(nextVal);
      window.requestAnimationFrame(() => {
        if (textareaRef.current) {
          textareaRef.current.selectionStart = start + 4;
          textareaRef.current.selectionEnd = start + 4;
        }
      });
    }
  };

  const handleScroll = (e) => {
    const st = e.target.scrollTop;
    setScrollTop(st);
    if (gutterRef.current) {
      gutterRef.current.scrollTop = st;
    }
  };

  const visibleTestsList = challenge.visibleTests || [];
  const selectedCase = visibleTestsList[selectedCaseIndex] || visibleTestsList[0];
  const selectedResult =
    visibleResults.find((r) => r.test === (selectedCase?.test || selectedCaseIndex + 1)) ||
    visibleResults[selectedCaseIndex];
  const selectedOutcome = selectedResult ? selectedResult.outcome : null;
  const selectedGot =
    selectedResult && selectedResult.got !== undefined && selectedResult.got !== null
      ? selectedResult.got
      : selectedOutcome === 'passed'
      ? selectedCase?.expected
      : '';

  return (
    <div className="workspace-shell">
      <Header
        currentPath={`/challenges/${challenge.id}`}
        onNavigate={onNavigate}
        learnerName={learnerName}
        onUpdateLearnerName={onUpdateLearnerName}
      />

      <div className="workspace-topbar">
        <div className="workspace-topbar__left">
          <button
            type="button"
            className="workspace-back-btn"
            onClick={() => onNavigate('/challenges')}
          >
            <span aria-hidden="true">←</span>
            <span>Problem List</span>
          </button>

          <h1 className="workspace-problem-title">{challenge.title}</h1>
          <GradeBadge grade={challenge.grade} difficulty={challenge.difficulty} size="sm" />

          {(challenge.tags || []).map((tag) => (
            <span key={tag} className="topic-pill">
              {tag}
            </span>
          ))}
        </div>

        <div className="workspace-topbar__right">
          <div className="workspace-sandbox-pill" aria-live="polite">
            <span
              className={`workspace-sandbox-pill__dot ${
                isRunning ? 'workspace-sandbox-pill__dot--busy' : ''
              }`}
              aria-hidden="true"
            />
            <span>{sandboxStatus}</span>
          </div>

          <button
            type="button"
            className="btn-secondary"
            onClick={handleResetCode}
            title="Restore initial starter code"
          >
            Reset Code
          </button>

          <button
            type="button"
            className="btn-secondary"
            onClick={() => handleGetHint()}
            disabled={isFetchingHint || remainingHints === 0}
          >
            <span aria-hidden="true">💡</span>
            <span>
              {isFetchingHint
                ? 'Loading Hint…'
                : remainingHints > 0
                ? `Get Hint (${4 - remainingHints}/4)`
                : 'All 4 Hints Unlocked'}
            </span>
          </button>

          <button
            type="button"
            className="btn-success"
            onClick={handleRun}
            disabled={isRunning}
            title="Run Visible & Hidden Tests (Ctrl+Enter)"
          >
            <span aria-hidden="true">▶</span>
            <span>{isRunning ? 'Running…' : 'Run & Submit'}</span>
          </button>
        </div>
      </div>

      <main className="workspace-grid">
        {/* LEFT PANE: Problem Description + AI Coach & Hints */}
        <section className="workspace-pane" aria-label="Problem description and diagnostics">
          <div className="pane-tabs" role="tablist">
            <button
              type="button"
              role="tab"
              aria-selected={leftTab === 'description'}
              className={`pane-tab ${leftTab === 'description' ? 'pane-tab--active' : ''}`}
              onClick={() => setLeftTab('description')}
            >
              Description
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={leftTab === 'coach'}
              className={`pane-tab ${leftTab === 'coach' ? 'pane-tab--active' : ''}`}
              onClick={() => setLeftTab('coach')}
            >
              <span>AI Coach &amp; Hints</span>
              {(revealedHints.length > 0 || hasFailedTests) && (
                <span className="pane-tab__count">
                  {revealedHints.length > 0 ? `${revealedHints.length}/4` : '!'}
                </span>
              )}
            </button>
          </div>

          {leftTab === 'description' ? (
            <div className="pane-body">
              {challenge.function_signature && (
                <div>
                  <h2 className="problem-section-label">Function Signature</h2>
                  <div className="problem-signature-box">
                    <code>{challenge.function_signature}</code>
                  </div>
                </div>
              )}

              <div>
                <h2 className="problem-section-label">Problem Statement</h2>
                <p className="problem-statement-text">{challenge.statement}</p>
              </div>

              {challenge.example && (
                <div>
                  <h2 className="problem-section-label">Example</h2>
                  <div className="example-card">
                    <div className="example-row">
                      <span className="example-row__label">Call:</span>
                      <code>{challenge.example.call}</code>
                    </div>
                    <div className="example-row">
                      <span className="example-row__label">Expected:</span>
                      <code>{challenge.example.expected}</code>
                    </div>
                    {challenge.example.explanation && (
                      <div className="example-row">
                        <span className="example-row__label">Note:</span>
                        <span>{challenge.example.explanation}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {challenge.constraints && (
                <div>
                  <h2 className="problem-section-label">Execution Constraints</h2>
                  <ul className="constraints-list">
                    {challenge.constraints.input_constraints && (
                      <li>Input bounds: <code>{challenge.constraints.input_constraints}</code></li>
                    )}
                    {challenge.constraints.time_limit_ms && (
                      <li>Time limit: {challenge.constraints.time_limit_ms}ms per test case</li>
                    )}
                    {challenge.constraints.memory_limit_mb && (
                      <li>Memory limit: {challenge.constraints.memory_limit_mb}MB</li>
                    )}
                    {challenge.constraints.time_complexity && (
                      <li>Target complexity: <code>{challenge.constraints.time_complexity}</code></li>
                    )}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className="pane-body">
              {/* Plain-Language "What Went Wrong" Explanation */}
              <div
                className={`diagnostic-banner ${
                  hasRun
                    ? allPassed
                      ? 'diagnostic-banner--pass'
                      : 'diagnostic-banner--fail'
                    : ''
                }`}
              >
                <h2 className="diagnostic-banner__title">
                  {!hasRun
                    ? 'Diagnostic Summary'
                    : allPassed
                    ? '✓ All Visible & Hidden Tests Passed'
                    : 'What Went Wrong'}
                </h2>
                <p className="diagnostic-banner__text">
                  {!hasRun
                    ? 'Run your code in the sandbox to see a plain-language explanation of any failing visible or hidden edge cases.'
                    : explanation || 'Review the test console on the right for detailed test results.'}
                </p>

                {mistakeTags.length > 0 && (
                  <div className="mistake-tags-row" aria-label="Detected mistake categories">
                    {mistakeTags.map((tag) => (
                      <span key={tag} className="mistake-tag-badge">
                        <span>⚠</span>
                        <span>{tag}</span>
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* AI Debugging Mascot Helper Station */}
              <div className="ai-helper-card">
                <div className="ai-helper-header">
                  <div className="ai-helper-identity">
                    <img
                      src={botAvatarImg}
                      alt="AI Debugging Helper"
                      className="ai-helper-avatar"
                    />
                    <div>
                      <span className="ai-helper-title">AI Debugging Assistant</span>
                      <span className="ai-helper-subtitle">
                        {botActive
                          ? `Inspecting Line ${targetLine} in editor`
                          : hasFailedTests
                          ? `Suspect issue near Line ${suspectErrorLine}`
                          : 'Progressive 4-step hints without answer spoilers'}
                      </span>
                    </div>
                  </div>

                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => {
                      if (botActive) {
                        setBotActive(false);
                      } else {
                        handleDeployBot();
                      }
                    }}
                  >
                    {botActive ? 'Dismiss from Editor' : `Highlight Line ${hasFailedTests ? suspectErrorLine : activeLine}`}
                  </button>
                </div>

                {/* 4-Step Progressive Hint Ladder */}
                <div className="hint-steps-bar" aria-label="Progressive hint steps">
                  {[1, 2, 3, 4].map((step) => {
                    const isUnlocked = revealedHints.some((h) => h.index === step);
                    return (
                      <div
                        key={step}
                        className={`hint-step-pill ${isUnlocked ? 'hint-step-pill--unlocked' : ''}`}
                      >
                        Hint {step} {isUnlocked ? '✓' : '🔒'}
                      </div>
                    );
                  })}
                </div>

                {revealedHints.length > 0 ? (
                  <div className="hint-ladder-list">
                    {revealedHints.map((h) => (
                      <div key={h.index} className="hint-card">
                        <div className="hint-card__header">
                          <span>{HINT_STEP_TITLES[h.index] || `Hint ${h.index}`}</span>
                          <span>{h.index} / 4</span>
                        </div>
                        <p className="hint-card__text">{h.text}</p>

                        {h.index === 4 && !h.code_patch && (
                          <div style={{ marginTop: '10px' }}>
                            <button
                              type="button"
                              className="btn-secondary"
                              onClick={() => handleGetHint({ level: 4, includePatch: true })}
                              disabled={isFetchingHint}
                            >
                              Show Suggested Code Patch (Optional)
                            </button>
                          </div>
                        )}

                        {h.code_patch && (
                          <div className="bot-patch-box">
                            <div className="bot-patch-header">
                              <span className="bot-patch-tag">
                                Suggested Fix (Line {h.code_patch.target_line})
                              </span>
                            </div>
                            <div className="bot-patch-diff">
                              {h.code_patch.original_snippet && (
                                <div className="bot-diff-line bot-diff-line--del">
                                  <span>-</span>
                                  <code>{h.code_patch.original_snippet}</code>
                                </div>
                              )}
                              <div className="bot-diff-line bot-diff-line--add">
                                <span>+</span>
                                <code>{h.code_patch.replacement_snippet}</code>
                              </div>
                            </div>
                            {patchApplied ? (
                              <div className="bot-patch-success">
                                ✓ Patch applied! Click Run &amp; Submit to verify.
                              </div>
                            ) : (
                              <button
                                type="button"
                                className="bot-patch-apply-btn"
                                onClick={() => handleApplyCodePatch(h.code_patch)}
                              >
                                Apply Fix to Line {h.code_patch.target_line}
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="ai-helper-subtitle">
                    Stuck on a failing test? Unlock Hint 1 for a gentle nudge on where to look, without spoiling the solution.
                  </p>
                )}

                {remainingHints > 0 && revealedHints.length < 4 && (
                  <div>
                    <button
                      type="button"
                      className="btn-primary"
                      onClick={() => handleGetHint()}
                      disabled={isFetchingHint}
                    >
                      <span>
                        {isFetchingHint
                          ? 'Generating Hint…'
                          : `Unlock Hint ${revealedHints.length + 1} of 4 (${remainingHints} remaining)`}
                      </span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}
        </section>

        {/* RIGHT PANE: Python 3 Editor + Docked Test Console */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <section className="workspace-pane" aria-label="Python 3 code editor">
            <div className="editor-header">
              <div className="editor-lang-tag">
                <span>Python 3</span>
                <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>solution.py</span>
              </div>

              <div className="editor-actions">
                <span style={{ fontSize: '11.5px', color: 'var(--text-muted)' }}>
                  Ln {activeLine}
                </span>
                <button
                  type="button"
                  className="btn-secondary"
                  style={{ padding: '4px 10px', fontSize: '12px' }}
                  onClick={() => {
                    if (botActive) {
                      setBotActive(false);
                    } else {
                      handleDeployBot();
                    }
                  }}
                >
                  <img
                    src={botAvatarImg}
                    alt=""
                    style={{ width: '16px', height: '16px', borderRadius: '50%' }}
                  />
                  <span>
                    {botActive
                      ? `Hide Helper (Ln ${targetLine})`
                      : hasFailedTests
                      ? `Inspect Suspect Line (${suspectErrorLine})`
                      : `Inspect Line ${activeLine}`}
                  </span>
                </button>
              </div>
            </div>

            <div className="schematic-editor-body-wrapper">
              <div className="schematic-gutter" ref={gutterRef} aria-hidden="true">
                {codeLines.map((_, i) => {
                  const lineNum = i + 1;
                  const isTarget = botActive && targetLine === lineNum;
                  const isCursor = activeLine === lineNum;
                  return (
                    <div
                      key={`gutter-${lineNum}`}
                      className={`schematic-gutter-line ${
                        isTarget ? 'schematic-gutter-line--active' : ''
                      } ${isCursor ? 'schematic-gutter-line--cursor' : ''}`}
                    >
                      {lineNum}
                    </div>
                  );
                })}
              </div>

              <div className="schematic-editor-surface">
                {botActive && targetLine && (
                  <div
                    className={`editor-line-highlight ${
                      patchApplied
                        ? 'editor-line-highlight--patched'
                        : botMode === 'error'
                        ? 'editor-line-highlight--error'
                        : ''
                    }`}
                    style={{
                      top: `${(targetLine - 1) * 24 + 14 - scrollTop}px`
                    }}
                  />
                )}

                <textarea
                  ref={textareaRef}
                  className="code-textarea"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  onClick={handleCursorChange}
                  onKeyUp={handleCursorChange}
                  onSelect={handleCursorChange}
                  onKeyDown={handleKeyDown}
                  onScroll={handleScroll}
                  aria-label="Python code editor"
                  spellCheck={false}
                />

                {botActive && targetLine && (
                  <div
                    className="editor-floating-bot"
                    style={{
                      top: `${Math.max(8, (targetLine - 1) * 24 + 10 - scrollTop)}px`
                    }}
                  >
                    <div
                      className="floating-bot-avatar"
                      onClick={() => setBotActive(false)}
                      title="Dismiss helper"
                    >
                      <img src={botAvatarImg} alt="AI Helper Mascot" className="floating-bot-img" />
                    </div>

                    <div className="bot-speech-bubble" role="dialog" aria-label="Line diagnostic">
                      <div className="bot-speech-bubble-header">
                        <span className="bot-bubble-tag">
                          {botMode === 'error'
                            ? `Line ${targetLine} · ${botDiagnostic.title}`
                            : `Line ${targetLine} · Hint Helper`}
                        </span>
                        <button
                          type="button"
                          className="bot-bubble-close-btn"
                          onClick={() => setBotActive(false)}
                          aria-label="Close helper"
                        >
                          ✕
                        </button>
                      </div>

                      <p className="bot-speech-detail">
                        {botMode === 'error'
                          ? botDiagnostic.detail
                          : latestHint
                          ? latestHint.text
                          : 'Request a progressive hint below to inspect this logic step by step.'}
                      </p>

                      {botDiagnostic.lineSnippet && (
                        <div className="bot-code-snippet">
                          <code>{botDiagnostic.lineSnippet}</code>
                        </div>
                      )}

                      <div className="bot-speech-bubble-footer">
                        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                          {4 - remainingHints}/4 hints used
                        </span>
                        {remainingHints > 0 && (
                          <button
                            type="button"
                            className="bot-bubble-action-btn"
                            disabled={isFetchingHint}
                            onClick={() => handleGetHint()}
                          >
                            {isFetchingHint ? 'Loading…' : 'Next Hint →'}
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </section>

          {/* Docked Test Console */}
          <section className="workspace-pane console-container" aria-label="Test cases and results">
            <div className="pane-tabs" role="tablist">
              <button
                type="button"
                role="tab"
                aria-selected={consoleTab === 'testcase'}
                className={`pane-tab ${consoleTab === 'testcase' ? 'pane-tab--active' : ''}`}
                onClick={() => setConsoleTab('testcase')}
              >
                Testcase ({visibleTestsList.length})
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={consoleTab === 'result'}
                className={`pane-tab ${consoleTab === 'result' ? 'pane-tab--active' : ''}`}
                onClick={() => setConsoleTab('result')}
              >
                <span>Test Result</span>
                {hasRun && (
                  <span className="pane-tab__count">
                    {visiblePassed + hiddenPassed}/{visibleTotal + hiddenTotal}
                  </span>
                )}
              </button>
            </div>

            {consoleTab === 'testcase' ? (
              <div className="console-body">
                <div className="testcase-tabs">
                  {visibleTestsList.map((tc, idx) => (
                    <button
                      key={`tc-tab-${idx}`}
                      type="button"
                      className={`testcase-pill ${
                        selectedCaseIndex === idx ? 'testcase-pill--active' : ''
                      }`}
                      onClick={() => setSelectedCaseIndex(idx)}
                    >
                      Case {idx + 1}
                    </button>
                  ))}
                </div>

                {selectedCase && (
                  <div className="testcase-detail-grid">
                    <div className="testcase-field">
                      <span className="testcase-field__label">Function Call</span>
                      <code className="testcase-field__val">{selectedCase.call}</code>
                    </div>
                    <div className="testcase-field">
                      <span className="testcase-field__label">Expected Return Value</span>
                      <code className="testcase-field__val">{selectedCase.expected}</code>
                    </div>
                  </div>
                )}
              </div>
            ) : !hasRun ? (
              <div className="console-body">
                <p style={{ margin: 0, fontSize: '13px', color: 'var(--text-secondary)' }}>
                  Click <strong>Run &amp; Submit</strong> (or press <code>Ctrl+Enter</code>) to execute your code against all visible and hidden test cases.
                </p>
              </div>
            ) : (
              <div className="console-body">
                <div
                  className={`verdict-banner ${
                    allPassed ? 'verdict-banner--passed' : 'verdict-banner--failed'
                  }`}
                >
                  <div style={{ fontWeight: 700, fontSize: '14px' }}>
                    {allPassed
                      ? '✓ Accepted — All Visible & Hidden Tests Passed'
                      : limitHit
                      ? `⚠ Stopped: ${limitHit.toUpperCase()} Limit Exceeded`
                      : `✕ ${visiblePassed}/${visibleTotal} Visible Passed · ${hiddenPassed}/${hiddenTotal} Hidden Passed`}
                  </div>
                  <div style={{ fontSize: '12px' }}>
                    Total: {visiblePassed + hiddenPassed} / {visibleTotal + hiddenTotal} passed
                  </div>
                </div>

                {/* Visible Test Cases Section */}
                <div>
                  <h3 className="problem-section-label">
                    Visible Test Cases ({visiblePassed}/{visibleTotal} Passed)
                  </h3>
                  <div className="testcase-tabs" style={{ marginBottom: '10px' }}>
                    {visibleTestsList.map((tc, idx) => {
                      const res =
                        visibleResults.find((r) => r.test === (tc.test || idx + 1)) ||
                        visibleResults[idx];
                      const outcome = res?.outcome || 'pending';
                      return (
                        <button
                          key={`res-tab-${idx}`}
                          type="button"
                          className={`testcase-pill testcase-pill--${outcome} ${
                            selectedCaseIndex === idx ? 'testcase-pill--active' : ''
                          }`}
                          onClick={() => setSelectedCaseIndex(idx)}
                        >
                          <span aria-hidden="true">{getOutcomeIcon(outcome)}</span>
                          <span>Case {idx + 1}</span>
                          <span>· {formatOutcome(outcome)}</span>
                        </button>
                      );
                    })}
                  </div>

                  {selectedCase && (
                    <div className="testcase-detail-grid">
                      <div className="testcase-field">
                        <span className="testcase-field__label">Call</span>
                        <code className="testcase-field__val">{selectedCase.call}</code>
                      </div>
                      <div className="testcase-field">
                        <span className="testcase-field__label">Expected Output</span>
                        <code className="testcase-field__val">{selectedCase.expected}</code>
                      </div>
                      <div className="testcase-field">
                        <span className="testcase-field__label">
                          Actual Output ({formatOutcome(selectedOutcome)})
                        </span>
                        <code className="testcase-field__val">
                          {selectedGot !== '' ? String(selectedGot) : '—'}
                        </code>
                      </div>
                    </div>
                  )}
                </div>

                {/* Hidden Test Cases Section (Outcomes Only — Never Exposes Inputs/Outputs) */}
                <div>
                  <h3 className="problem-section-label">
                    Hidden Edge-Case Suite ({hiddenPassed}/{hiddenTotal} Passed · Inputs Locked)
                  </h3>
                  <div className="hidden-tests-grid">
                    {hiddenResults.map((hr, idx) => {
                      const testNum = hr.test || idx + 1;
                      const outcome = hr.outcome || 'pending';
                      return (
                        <div
                          key={`hid-${testNum}`}
                          className={`hidden-test-chip hidden-test-chip--${outcome}`}
                        >
                          <span style={{ fontWeight: 600 }}>🔒 Hidden #{testNum}</span>
                          <span>
                            {getOutcomeIcon(outcome)} {formatOutcome(outcome)}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
