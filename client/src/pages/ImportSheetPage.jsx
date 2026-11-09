import { useState, useEffect } from 'react';
import Header from '../components/Header.jsx';
import {
  getCuratedSheets,
  generateAITestCases,
  importSingleProblem,
} from '../services/api.js';

export default function ImportSheetPage({ onNavigate, learnerName = 'zeroeight', onUpdateLearnerName }) {
  const [activeTab, setActiveTab] = useState('curated'); // 'curated' | 'custom'
  const [sheets, setSheets] = useState([]);
  const [selectedSheetId, setSelectedSheetId] = useState('strivers-a2z');
  const [selectedCategory, setSelectedCategory] = useState('All');

  // Auto-generate edge cases toggle
  const [autoGenEdgeCases, setAutoGenEdgeCases] = useState(true);

  // Problem preview & edge case generation state
  const [previewingId, setPreviewingId] = useState(null);
  const [generatedData, setGeneratedData] = useState({}); // { [problemId]: { visible_tests, hidden_tests, hints } }
  const [importedStatus, setImportedStatus] = useState({}); // { [problemId]: true }
  const [importingId, setImportingId] = useState(null);

  // Batch import state
  const [isBatchImporting, setIsBatchImporting] = useState(false);
  const [batchProgress, setBatchProgress] = useState({ current: 0, total: 0, text: '' });
  const [terminalLogs, setTerminalLogs] = useState([]);

  // Custom problem form state
  const [customTitle, setCustomTitle] = useState('');
  const [customStatement, setCustomStatement] = useState('');
  const [customSignature, setCustomSignature] = useState('');
  const [customStarterCode, setCustomStarterCode] = useState('');
  const [customDifficulty, setCustomDifficulty] = useState('Medium');
  const [customTags, setCustomTags] = useState('Arrays, Algorithms');
  const [customGeneratedTests, setCustomGeneratedTests] = useState(null);
  const [customIsGenerating, setCustomIsGenerating] = useState(false);
  const [customImportSuccess, setCustomImportSuccess] = useState(null);

  useEffect(() => {
    let active = true;
    getCuratedSheets()
      .then((data) => {
        if (active && Array.isArray(data)) {
          setSheets(data);
          if (data.length > 0) {
            setSelectedSheetId(data[0].id);
          }
        }
      })
      .catch(() => {});
    return () => { active = false; };
  }, []);

  const currentSheet = sheets.find((s) => s.id === selectedSheetId) || sheets[0];

  const filteredProblems = (currentSheet?.problems || []).filter((p) => {
    if (selectedCategory === 'All') return true;
    return p.category === selectedCategory || (p.tags && p.tags.includes(selectedCategory));
  });

  const addLog = (msg) => {
    setTerminalLogs((prev) => [...prev.slice(-30), `[${new Date().toLocaleTimeString()}] ${msg}`]);
  };

  // Import a single problem into the database
  const handleImportProblem = async (problem) => {
    setImportingId(problem.id);
    addLog(`Persisting "${problem.title}" to database test harness...`);

    try {
      const gen = generatedData[problem.id];
      const payload = {
        id: problem.id,
        slug: problem.id,
        title: problem.title,
        statement: problem.statement,
        function_signature: problem.function_signature || '',
        starter_code: problem.starter_code || '',
        difficulty: problem.difficulty || 'Medium',
        tags: problem.tags || [],
        auto_generate_tests: autoGenEdgeCases && !gen,
        visible_tests: gen?.visible_tests || [],
        hidden_tests: gen?.hidden_tests || [],
        hints: gen?.hints || [],
      };

      const res = await importSingleProblem(payload);
      setImportedStatus((prev) => ({ ...prev, [problem.id]: true }));
      addLog(`✓ Successfully imported "${problem.title}" [${res.visible_test_count} visible, ${res.hidden_test_count} edge cases].`);
    } catch (err) {
      addLog(`✕ Failed to import "${problem.title}": ${err.message}`);
    } finally {
      setImportingId(null);
    }
  };

  // Batch import all problems from the current sheet
  const handleBatchImport = async () => {
    if (isBatchImporting || !currentSheet) return;
    setIsBatchImporting(true);
    const total = filteredProblems.length;
    setBatchProgress({ current: 0, total, text: 'Initializing sheet ingestion…' });
    addLog(`=== STARTING BATCH IMPORT: ${currentSheet.name} (${total} problems) ===`);

    try {
      for (let i = 0; i < total; i++) {
        const p = filteredProblems[i];
        setBatchProgress({ current: i + 1, total, text: `Processing ${p.title} (${i + 1}/${total})…` });
        addLog(`[${i + 1}/${total}] Generating edge cases & seeding: "${p.title}"...`);

        try {
          const gen = generatedData[p.id];
          const payload = {
            id: p.id,
            slug: p.id,
            title: p.title,
            statement: p.statement,
            function_signature: p.function_signature || '',
            starter_code: p.starter_code || '',
            difficulty: p.difficulty || 'Medium',
            tags: p.tags || [],
            auto_generate_tests: autoGenEdgeCases && !gen,
            visible_tests: gen?.visible_tests || [],
            hidden_tests: gen?.hidden_tests || [],
            hints: gen?.hints || [],
          };
          await importSingleProblem(payload);
          setImportedStatus((prev) => ({ ...prev, [p.id]: true }));
          addLog(`✓ "${p.title}" imported successfully.`);
        } catch (innerErr) {
          addLog(`⚠ Error on "${p.title}": ${innerErr.message}`);
        }
      }
      addLog(`=== BATCH IMPORT COMPLETE: All ${total} problems ready in Workbench! ===`);
    } catch (err) {
      addLog(`✕ Batch import aborted: ${err.message}`);
    } finally {
      setIsBatchImporting(false);
    }
  };

  // Custom problem: Generate edge cases with AI
  const handleCustomGenerate = async () => {
    if (!customTitle || !customStatement) return;
    setCustomIsGenerating(true);
    try {
      const res = await generateAITestCases({
        title: customTitle,
        statement: customStatement,
        function_signature: customSignature,
        starter_code: customStarterCode,
        difficulty: customDifficulty,
        tags: customTags.split(',').map((t) => t.trim()).filter(Boolean),
      });
      setCustomGeneratedTests(res);
      if (!customSignature && res.function_name) {
        setCustomSignature(`def ${res.function_name}(...):`);
      }
    } catch (err) {
      alert(`Generation failed: ${err.message}`);
    } finally {
      setCustomIsGenerating(false);
    }
  };

  // Custom problem: Save to database
  const handleCustomImport = async () => {
    if (!customTitle || !customStatement) return;
    try {
      const slug = customTitle.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
      const payload = {
        title: customTitle,
        slug,
        statement: customStatement,
        function_signature: customSignature,
        starter_code: customStarterCode || (customSignature ? `${customSignature}\n    pass\n` : ''),
        difficulty: customDifficulty,
        tags: customTags.split(',').map((t) => t.trim()).filter(Boolean),
        auto_generate_tests: !customGeneratedTests,
        visible_tests: customGeneratedTests?.visible_tests || [],
        hidden_tests: customGeneratedTests?.hidden_tests || [],
        hints: customGeneratedTests?.hints || [],
      };
      const res = await importSingleProblem(payload);
      setCustomImportSuccess(res);
    } catch (err) {
      alert(`Import failed: ${err.message}`);
    }
  };

  return (
    <div className="page-shell">
      <Header currentPath="/import" onNavigate={onNavigate} learnerName={learnerName} onUpdateLearnerName={onUpdateLearnerName} />

      <main className="content-container">
        {/* Breadcrumb Navigation */}
        <nav className="breadcrumbs" aria-label="Breadcrumb navigation">
          <button type="button" className="breadcrumb-link" onClick={() => onNavigate('/challenges')}>
            ← Challenges Archive
          </button>
          <span className="breadcrumb-separator" aria-hidden="true">/</span>
          <span className="breadcrumb-current" aria-current="page">Sheet Importer &amp; AI Edge-Case Generator</span>
        </nav>

        {/* Section Wireframe Bar */}
        <div className="schematic-section-bar">
          <div className="schematic-section-bar__left">
            <span># INGESTION_PIPELINE // SHEET_IMPORTER</span>
            <span className="schematic-section-bar__tag">[ AI EDGE-CASE HARNESS ]</span>
          </div>
          <span className="schematic-section-bar__tag">OPENROUTER POWERED · ZERO-LEAKAGE DB SEED</span>
        </div>

        {/* Mode Switcher Tabs */}
        <div className="importer-tabs-bar">
          <div className="importer-tabs">
            <button
              type="button"
              className={`importer-tab-btn ${activeTab === 'curated' ? 'importer-tab-btn--active' : ''}`}
              onClick={() => setActiveTab('curated')}
            >
              📚 CURATED SHEETS (STRIVER A2Z &amp; CP-31)
            </button>
            <button
              type="button"
              className={`importer-tab-btn ${activeTab === 'custom' ? 'importer-tab-btn--active' : ''}`}
              onClick={() => setActiveTab('custom')}
            >
              ⚡ CUSTOM PROBLEM / PASTE JSON
            </button>
          </div>

          <label className="importer-edge-toggle" title="When enabled, calls OpenRouter to generate comprehensive visible & hidden edge cases for each question">
            <input
              type="checkbox"
              checked={autoGenEdgeCases}
              onChange={(e) => setAutoGenEdgeCases(e.target.checked)}
            />
            <span className="importer-edge-toggle-text">⚡ Auto-Generate All Edge Cases via OpenRouter</span>
          </label>
        </div>

        {/* TAB 1: CURATED SHEETS */}
        {activeTab === 'curated' && (
          <div>
            {/* Sheet Selector Bar */}
            <div className="importer-sheet-cards-grid">
              {sheets.map((s) => {
                const isSelected = s.id === selectedSheetId;
                return (
                  <button
                    key={s.id}
                    type="button"
                    className={`importer-sheet-card ${isSelected ? 'importer-sheet-card--selected' : ''}`}
                    onClick={() => {
                      setSelectedSheetId(s.id);
                      setSelectedCategory('All');
                    }}
                  >
                    <div className="importer-sheet-card-top">
                      <span className="importer-sheet-badge">{s.badge}</span>
                      <span className="importer-sheet-count">{s.problem_count} Problems</span>
                    </div>
                    <h3 className="importer-sheet-title">{s.name}</h3>
                    <p className="importer-sheet-desc">{s.description}</p>
                  </button>
                );
              })}
            </div>

            {/* Action Toolbar & Category Filter */}
            <div className="importer-action-toolbar">
              <div className="importer-category-chips">
                <span className="importer-filter-label">Filter:</span>
                <button
                  type="button"
                  className={`category-chip ${selectedCategory === 'All' ? 'category-chip--active' : ''}`}
                  onClick={() => setSelectedCategory('All')}
                >
                  All ({currentSheet?.problem_count || 0})
                </button>
                {(currentSheet?.categories || []).map((cat) => (
                  <button
                    key={cat}
                    type="button"
                    className={`category-chip ${selectedCategory === cat ? 'category-chip--active' : ''}`}
                    onClick={() => setSelectedCategory(cat)}
                  >
                    {cat}
                  </button>
                ))}
              </div>

              <button
                type="button"
                className="primary-energy-btn importer-batch-btn"
                onClick={handleBatchImport}
                disabled={isBatchImporting}
              >
                <span>{isBatchImporting ? '⚡ INGESTING SHEET…' : `⚡ Batch Import All (${filteredProblems.length}) with Edge Cases`}</span>
              </button>
            </div>

            {/* Batch Progress Bar */}
            {isBatchImporting && (
              <div className="importer-progress-box">
                <div className="importer-progress-header">
                  <span>{batchProgress.text}</span>
                  <span>{batchProgress.current} / {batchProgress.total}</span>
                </div>
                <div className="importer-progress-track">
                  <div
                    className="importer-progress-fill"
                    style={{ width: `${(batchProgress.current / Math.max(1, batchProgress.total)) * 100}%` }}
                  />
                </div>
              </div>
            )}

            {/* Live Terminal Execution Logs */}
            {terminalLogs.length > 0 && (
              <div className="importer-terminal-box">
                <div className="importer-terminal-header">
                  <span className="file-dot" aria-hidden="true">●</span>
                  <span>[ INGESTION TERMINAL // OPENROUTER &amp; DB PIPELINE ]</span>
                  <button type="button" className="importer-terminal-clear" onClick={() => setTerminalLogs([])}>Clear</button>
                </div>
                <div className="importer-terminal-body">
                  {terminalLogs.map((log, idx) => (
                    <div key={`log-${idx}`} className="importer-log-line">{log}</div>
                  ))}
                </div>
              </div>
            )}

            {/* Problem Catalog List */}
            <div className="importer-problem-list">
              {filteredProblems.map((p) => {
                const isPreviewing = previewingId === p.id;
                const gen = generatedData[p.id];
                const isImported = importedStatus[p.id];
                const isImporting = importingId === p.id;

                return (
                  <div key={p.id} className={`importer-problem-card ${isImported ? 'importer-problem-card--imported' : ''}`}>
                    <div className="importer-problem-main">
                      <div className="importer-problem-info">
                        <div className="importer-problem-tags">
                          <span className={`difficulty-badge difficulty-badge--${p.difficulty.toLowerCase()}`}>
                            {p.difficulty}
                          </span>
                          <span className="importer-cat-tag">{p.category}</span>
                          {(p.tags || []).map((t) => (
                            <span key={t} className="importer-sub-tag">#{t}</span>
                          ))}
                        </div>
                        <h4 className="importer-problem-name">{p.title}</h4>
                        <p className="importer-problem-statement">{p.statement}</p>
                      </div>

                      <div className="importer-problem-actions">
                        {isImported ? (
                          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                            <span className="importer-success-stamp">✓ IN JUDGE</span>
                            <button
                              type="button"
                              className="secondary-btn importer-btn"
                              onClick={() => onNavigate(`/challenges/${p.id}`)}
                            >
                              Open in Workbench ➔
                            </button>
                          </div>
                        ) : (
                          <button
                            type="button"
                            className="primary-energy-btn importer-btn"
                            onClick={() => handleImportProblem(p)}
                            disabled={isImporting || isBatchImporting}
                          >
                            <span>{isImporting ? 'Importing…' : 'Import Problem'}</span>
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Edge-Cases Preview Accordion */}
                    {isPreviewing && (
                      <div className="importer-edge-preview-box">
                        <div className="importer-edge-preview-header">
                          <span className="bot-patch-tag">⚡ SYNTHESIZED EDGE-CASE HARNESS (OPENROUTER)</span>
                          <span className="schematic-section-bar__tag">
                            {gen?.visible_tests?.length || 0} VISIBLE + {gen?.hidden_tests?.length || 0} HIDDEN EDGE CASES
                          </span>
                        </div>

                        {gen ? (
                          <div>
                            {/* Visible Tests */}
                            <div className="importer-test-section-title">Visible Tests (Sample &amp; Examples):</div>
                            <div className="importer-tests-grid">
                              {(gen.visible_tests || []).map((t, idx) => (
                                <div key={`vis-${idx}`} className="importer-test-pill">
                                  <div className="importer-test-pill-header">
                                    <span className="importer-test-badge importer-test-badge--vis">VISIBLE #{t.test || idx + 1}</span>
                                    <span className="importer-test-desc">{t.description}</span>
                                  </div>
                                  <div className="importer-test-code"><code>{t.call}</code></div>
                                  <div className="importer-test-expected">Expected: <code>{t.expected}</code></div>
                                </div>
                              ))}
                            </div>

                            {/* Hidden Edge Cases */}
                            <div className="importer-test-section-title" style={{ marginTop: '12px' }}>
                              Hidden Edge Cases (Adversarial &amp; Boundary Defense):
                            </div>
                            <div className="importer-tests-grid">
                              {(gen.hidden_tests || []).map((t, idx) => (
                                <div key={`hid-${idx}`} className="importer-test-pill importer-test-pill--edge">
                                  <div className="importer-test-pill-header">
                                    <span className="importer-test-badge importer-test-badge--edge">EDGE CASE #{t.test || idx + 4}</span>
                                    <span className="importer-test-desc">{t.description}</span>
                                  </div>
                                  <div className="importer-test-code"><code>{t.call}</code></div>
                                  <div className="importer-test-expected">Expected: <code>{t.expected}</code></div>
                                </div>
                              ))}
                            </div>

                            {/* Generated Progressive Hints */}
                            {gen.hints && gen.hints.length > 0 && (
                              <div style={{ marginTop: '12px' }}>
                                <div className="importer-test-section-title">Calibrated Progressive Hint Ladder:</div>
                                <div className="importer-hints-ladder">
                                  {gen.hints.map((h, hidx) => (
                                    <div key={`h-${hidx}`} className="importer-hint-row">
                                      <span className="step-badge">Hint {hidx + 1}</span>
                                      <span className="schematic-text" style={{ fontSize: '12px' }}>{h}</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        ) : (
                          <div className="importer-loading-placeholder">
                            <span>Generating test suite and boundary edge cases via OpenRouter…</span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* TAB 2: CUSTOM PROBLEM IMPORTER */}
        {activeTab === 'custom' && (
          <div className="importer-custom-form-wrap">
            <div className="importer-custom-grid">
              {/* Form Column */}
              <div className="importer-custom-form">
                <h3 className="importer-section-title">Import Custom Question / LeetCode Specification</h3>

                <div className="importer-form-group">
                  <label className="importer-form-label">Problem Title *</label>
                  <input
                    type="text"
                    className="importer-form-input"
                    placeholder="e.g. Invert Binary Tree"
                    value={customTitle}
                    onChange={(e) => setCustomTitle(e.target.value)}
                  />
                </div>

                <div className="importer-form-row">
                  <div className="importer-form-group" style={{ flex: 1 }}>
                    <label className="importer-form-label">Difficulty</label>
                    <select
                      className="importer-form-input"
                      value={customDifficulty}
                      onChange={(e) => setCustomDifficulty(e.target.value)}
                    >
                      <option value="Easy">Easy (Grade 4)</option>
                      <option value="Medium">Medium (Grade 3)</option>
                      <option value="Hard">Hard (Grade 2)</option>
                    </select>
                  </div>

                  <div className="importer-form-group" style={{ flex: 2 }}>
                    <label className="importer-form-label">Tags (comma-separated)</label>
                    <input
                      type="text"
                      className="importer-form-input"
                      placeholder="e.g. Binary Tree, Recursion"
                      value={customTags}
                      onChange={(e) => setCustomTags(e.target.value)}
                    />
                  </div>
                </div>

                <div className="importer-form-group">
                  <label className="importer-form-label">Problem Statement &amp; Contract *</label>
                  <textarea
                    className="importer-form-textarea"
                    rows={4}
                    placeholder="Describe problem inputs, rules, and expected return value..."
                    value={customStatement}
                    onChange={(e) => setCustomStatement(e.target.value)}
                  />
                </div>

                <div className="importer-form-group">
                  <label className="importer-form-label">Function Signature / Starter Code</label>
                  <textarea
                    className="importer-form-textarea importer-form-code"
                    rows={4}
                    placeholder="def invert_tree(root):&#10;    # Your code here&#10;    pass"
                    value={customStarterCode}
                    onChange={(e) => setCustomStarterCode(e.target.value)}
                  />
                </div>

                <div className="importer-custom-actions">
                  <button
                    type="button"
                    className="secondary-btn importer-btn"
                    onClick={handleCustomGenerate}
                    disabled={customIsGenerating || !customTitle || !customStatement}
                  >
                    {customIsGenerating ? '⚡ Synthesizing Edge Cases…' : '⚡ Generate Edge Cases with AI'}
                  </button>

                  <button
                    type="button"
                    className="primary-energy-btn importer-btn"
                    onClick={handleCustomImport}
                    disabled={!customTitle || !customStatement}
                  >
                    <span>💾 Save Problem to Judge</span>
                  </button>
                </div>

                {customImportSuccess && (
                  <div className="importer-success-alert">
                    <span>✓ Successfully seeded "{customImportSuccess.title}" with {customImportSuccess.visible_test_count} visible and {customImportSuccess.hidden_test_count} hidden edge cases!</span>
                    <button
                      type="button"
                      className="secondary-btn importer-btn"
                      onClick={() => onNavigate(`/challenges/${customImportSuccess.slug}`)}
                    >
                      Open in Workbench ➔
                    </button>
                  </div>
                )}
              </div>

              {/* Edge Cases Preview Column */}
              <div className="importer-custom-preview">
                <h3 className="importer-section-title">Synthesized Edge Cases Preview</h3>
                {customGeneratedTests ? (
                  <div>
                    <div className="importer-test-section-title">Visible Tests (3):</div>
                    <div className="importer-tests-grid">
                      {customGeneratedTests.visible_tests.map((t, idx) => (
                        <div key={`cvis-${idx}`} className="importer-test-pill">
                          <div className="importer-test-pill-header">
                            <span className="importer-test-badge importer-test-badge--vis">TEST #{idx + 1}</span>
                            <span className="importer-test-desc">{t.description}</span>
                          </div>
                          <div className="importer-test-code"><code>{t.call}</code></div>
                          <div className="importer-test-expected">Expected: <code>{t.expected}</code></div>
                        </div>
                      ))}
                    </div>

                    <div className="importer-test-section-title" style={{ marginTop: '12px' }}>
                      Adversarial Hidden Edge Cases ({customGeneratedTests.hidden_tests.length}):
                    </div>
                    <div className="importer-tests-grid">
                      {customGeneratedTests.hidden_tests.map((t, idx) => (
                        <div key={`chid-${idx}`} className="importer-test-pill importer-test-pill--edge">
                          <div className="importer-test-pill-header">
                            <span className="importer-test-badge importer-test-badge--edge">EDGE #{idx + 4}</span>
                            <span className="importer-test-desc">{t.description}</span>
                          </div>
                          <div className="importer-test-code"><code>{t.call}</code></div>
                          <div className="importer-test-expected">Expected: <code>{t.expected}</code></div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="importer-preview-empty">
                    <p>Click <strong>"⚡ Generate Edge Cases with AI"</strong> to automatically synthesize:</p>
                    <ul>
                      <li>3 Canonical visible tests</li>
                      <li>Empty &amp; single-element edge cases</li>
                      <li>Negative, duplicate, and boundary edge cases</li>
                      <li>4-step calibrated progressive hint ladder</li>
                    </ul>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
