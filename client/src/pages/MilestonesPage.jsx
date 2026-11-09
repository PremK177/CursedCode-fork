import { useState, useEffect, useMemo } from 'react';
import Header from '../components/Header.jsx';
import Footer from '../components/Footer.jsx';
import GradeBadge from '../components/GradeBadge.jsx';
import { getChallenges, getLearnerProfile } from '../services/api.js';
import { CHALLENGES } from '../data/challenges.js';

const GRADE_LEVELS = [
  { threshold: 0, grade: 'Grade 4', difficulty: 'Easy' },
  { threshold: 0.2, grade: 'Grade 3', difficulty: 'Medium' },
  { threshold: 0.4, grade: 'Grade 2', difficulty: 'Hard' },
  { threshold: 0.6, grade: 'Semi-Grade 1', difficulty: 'Advanced' },
  { threshold: 0.8, grade: 'Grade 1', difficulty: 'Expert' },
  { threshold: 0.93, grade: 'Special Grade', difficulty: 'Supreme' }
];

function gradeFromScore(score) {
  return [...GRADE_LEVELS].reverse().find((level) => score >= level.threshold);
}

function learnerInitials(name) {
  const initials = name.trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join('');
  return initials.toUpperCase() || '?';
}

// Milestone Tree Node Definitions (Progressive Levels independent of grade)
const MILESTONE_NODES = [
  {
    id: 'lvl-0',
    level: 0,
    tier: 0,
    title: 'Initiate Spark',
    icon: '⚡',
    reqSolved: 0,
    subtitle: 'Entry into the Dojo',
    description: 'Awaken your computational instincts. The starting threshold where all cursed code exploration begins.',
    perks: ['Unlocked: Sandbox Execution Terminal', 'Unlocked: Real-time Output Inspection'],
    recommendedChallenges: ['last-k-total', 'count-passes']
  },
  {
    id: 'lvl-1',
    level: 1,
    tier: 1,
    branch: 'left',
    title: 'Sequence Apprentice',
    icon: '✦',
    reqSolved: 1,
    subtitle: 'List Slicing & Sequence Flow',
    description: 'Master negative offsets and sequence boundaries without succumbing to IndexError vulnerabilities.',
    perks: ['Unlocked: Diagnostic Mistake Taxonomy Tagging', 'Unlocked: Vector Verification Grid'],
    recommendedChallenges: ['last-k-total', 'first-n-squares']
  },
  {
    id: 'lvl-2',
    level: 2,
    tier: 1,
    branch: 'right',
    title: 'Flow Manipulator',
    icon: '⚔',
    reqSolved: 2,
    subtitle: 'Iterative Control & Predicates',
    description: 'Command conditional branching and accumulator loops with strict mathematical precision.',
    perks: ['Unlocked: Hint Ladder Diagnostic Bot', 'Unlocked: Iteration Tracing Telemetry'],
    recommendedChallenges: ['count-passes', 'middle-three']
  },
  {
    id: 'lvl-3',
    level: 3,
    tier: 2,
    branch: 'center',
    title: 'Technique Adept',
    icon: '🛡',
    reqSolved: 4,
    subtitle: 'Core Foundation Mastery',
    description: 'Convergence of sequence manipulation and algorithmic control. Errors are identified before execution.',
    perks: ['Unlocked: Performance Benchmarking (ms)', 'Unlocked: Hidden Vector Secrecy Vault'],
    recommendedChallenges: ['secondlargest', 'palindrometest']
  },
  {
    id: 'lvl-4',
    level: 4,
    tier: 3,
    branch: 'left',
    title: 'Boundary Weaver',
    icon: '🌀',
    reqSolved: 6,
    subtitle: 'Extreme Edge-Case Hardening',
    description: 'Handle empty inputs, boundary markers, and hostile test cases with zero runtime regressions.',
    perks: ['Unlocked: Red-Team Hostility Defense Analysis', 'Unlocked: Deep Logic Explanations'],
    recommendedChallenges: ['longestincreasing', 'mergesorted']
  },
  {
    id: 'lvl-5',
    level: 5,
    tier: 3,
    branch: 'right',
    title: 'Array Alchemist',
    icon: '👁',
    reqSolved: 8,
    subtitle: 'Structural Transformation',
    description: 'Transform, filter, and synthesize complex multidimensional collections with optimal spatial efficiency.',
    perks: ['Unlocked: Memory Limit Containment Telemetry', 'Unlocked: Advanced Tree Branch Analysis'],
    recommendedChallenges: ['rotateksteps', 'groupanagrams']
  },
  {
    id: 'lvl-6',
    level: 6,
    tier: 4,
    branch: 'center',
    title: 'Domain Construct',
    icon: '⛩',
    reqSolved: 10,
    subtitle: 'High-Complexity Synthesis',
    description: 'Construct impenetrable algorithmic domains. Solve advanced challenges with near-zero hint reliance.',
    perks: ['Unlocked: Apex Diagnostic Insight', 'Unlocked: Grandmaster Candidate Profile'],
    recommendedChallenges: ['trappingwater', 'validparentheses']
  },
  {
    id: 'lvl-7',
    level: 7,
    tier: 5,
    branch: 'apex',
    title: 'Limitless Grandmaster',
    icon: '👑',
    reqSolved: 12,
    subtitle: 'Total Problem Dominion',
    description: 'Every challenge vector conquered. Complete algorithmic clarity achieved across the entire test suite.',
    perks: ['Unlocked: Full CursedCode Completion Honor', 'Unlocked: Special Recognition Seal'],
    recommendedChallenges: []
  }
];

export default function MilestonesPage({ onNavigate, learnerName = 'zeroeight', onUpdateLearnerName }) {
  const [challenges, setChallenges] = useState(CHALLENGES);
  const [selectedNodeId, setSelectedNodeId] = useState('lvl-0');
  const [profile, setProfile] = useState();

  useEffect(() => {
    let active = true;
    getChallenges(learnerName)
      .then((data) => {
        if (active && Array.isArray(data) && data.length > 0) {
          setChallenges(data);
        }
      })
      .catch(() => {
        // Fallback to initial local challenges
      });
    return () => { active = false; };
  }, [learnerName]);

  useEffect(() => {
    let active = true;
    getLearnerProfile(learnerName).then((data) => {
      if (active) setProfile(data);
    });
    return () => { active = false; };
  }, [learnerName]);

  // Compute number of solved problems
  const solvedChallenges = useMemo(() => {
    return challenges.filter((c) => c.status === 'Solved' || c.status === 'passed');
  }, [challenges]);

  const solvedCount = solvedChallenges.length;
  const totalCount = challenges.length || 12;

  const overallMastery = useMemo(() => {
    if (!Array.isArray(profile?.mastery) || profile.mastery.length === 0) return null;
    const scores = profile.mastery
      .map((item) => Number(item?.score ?? item?.estimate))
      .filter((score) => Number.isFinite(score) && score >= 0 && score <= 1);
    if (scores.length === 0) return null;
    return scores.reduce((total, score) => total + score, 0) / scores.length;
  }, [profile]);
  const learnerGrade = overallMastery === null ? null : gradeFromScore(overallMastery);

  // Determine current active level based on solvedCount (independent of grade)
  const currentLevelNode = useMemo(() => {
    let current = MILESTONE_NODES[0];
    for (const node of MILESTONE_NODES) {
      if (solvedCount >= node.reqSolved) {
        current = node;
      }
    }
    return current;
  }, [solvedCount]);

  // Next level milestone to achieve
  const nextLevelNode = useMemo(() => {
    return MILESTONE_NODES.find((node) => node.reqSolved > solvedCount) || null;
  }, [solvedCount]);

  // Calculate progress toward next level
  const progressToNext = useMemo(() => {
    if (!nextLevelNode) return 100;
    const prevReq = currentLevelNode.reqSolved;
    const nextReq = nextLevelNode.reqSolved;
    const progressInTier = solvedCount - prevReq;
    const span = Math.max(1, nextReq - prevReq);
    return Math.min(100, Math.round((progressInTier / span) * 100));
  }, [solvedCount, currentLevelNode, nextLevelNode]);

  // Sync initial selected node to current level on load
  useEffect(() => {
    if (currentLevelNode) {
      setSelectedNodeId(currentLevelNode.id);
    }
  }, [currentLevelNode]);

  const selectedNode = useMemo(() => {
    return MILESTONE_NODES.find((n) => n.id === selectedNodeId) || currentLevelNode;
  }, [selectedNodeId, currentLevelNode]);

  // Group nodes by tier for the tree layout
  const tier0Nodes = MILESTONE_NODES.filter((n) => n.tier === 0);
  const tier1Nodes = MILESTONE_NODES.filter((n) => n.tier === 1);
  const tier2Nodes = MILESTONE_NODES.filter((n) => n.tier === 2);
  const tier3Nodes = MILESTONE_NODES.filter((n) => n.tier === 3);
  const tier4Nodes = MILESTONE_NODES.filter((n) => n.tier === 4);
  const tier5Nodes = MILESTONE_NODES.filter((n) => n.tier === 5);

  const getNodeState = (node) => {
    if (solvedCount >= node.reqSolved) {
      if (node.id === currentLevelNode.id) return 'current';
      return 'completed';
    }
    if (nextLevelNode && node.id === nextLevelNode.id) return 'next';
    return 'locked';
  };

  return (
    <div className="page-shell">
      <Header currentPath="/milestones" onNavigate={onNavigate} learnerName={learnerName} onUpdateLearnerName={onUpdateLearnerName} />

      <main className="content-container">
        {/* Page Intro Header */}
        <section className="page-intro">
          <p className="eyebrow">
            <span className="eyebrow-accent">// LEVEL TREE ROADMAP</span>
            <span>Evolutionary Progression System</span>
          </p>
          <div className="intro-header">
            <h1 className="page-title">
              MILESTONE TREE &amp;<br />
              <span className="title-highlight">LEVEL ROADMAP.</span>
            </h1>
            <p className="intro-lead">
              Your level rises strictly as you solve problems — completely independent of problem grade or difficulty.
              Conquer challenges, illuminate branches of the tree, and unlock higher developmental tiers.
            </p>
          </div>
        </section>

        <section className="milestone-profile-card" aria-label="Learner profile">
          <div className="milestone-profile-avatar" aria-hidden="true">{learnerInitials(learnerName)}</div>
          <div className="milestone-profile-identity">
            <span className="milestone-profile-kicker">LEARNER PROFILE</span>
            <h2>{learnerName}</h2>
            <span className="milestone-profile-level">Level {currentLevelNode.level} · {currentLevelNode.title}</span>
          </div>
          <div className="milestone-profile-mastery">
            <span className="milestone-profile-kicker">OVERALL MASTERY</span>
            {learnerGrade ? (
              <div className="milestone-profile-grade">
                <GradeBadge grade={learnerGrade.grade} difficulty={learnerGrade.difficulty} />
                <span>{overallMastery.toFixed(2)}</span>
              </div>
            ) : (
              <span className="milestone-profile-empty">
                {profile === undefined
                  ? 'Loading mastery…'
                  : profile === null
                  ? 'Mastery unavailable'
                  : 'No mastery scores yet'}
              </span>
            )}
          </div>
          <div className="milestone-profile-solved">
            <strong>{solvedCount}</strong>
            <span>challenges solved</span>
          </div>
        </section>

        {/* Current Level Dashboard Hero Bar */}
        <div className="milestone-hero-banner">
          <div className="milestone-hero-left">
            <div className="milestone-level-badge">
              <span className="milestone-level-badge__icon">{currentLevelNode.icon}</span>
              <div className="milestone-level-badge__text">
                <span className="milestone-level-badge__tag">CURRENT STATUS</span>
                <span className="milestone-level-badge__title">LEVEL {currentLevelNode.level}: {currentLevelNode.title.toUpperCase()}</span>
              </div>
            </div>

            <div className="milestone-hero-stats">
              <div className="milestone-stat-item">
                <span className="milestone-stat-label">PROBLEMS SOLVED</span>
                <span className="milestone-stat-val">
                  <strong>{solvedCount}</strong> / {totalCount}
                </span>
              </div>
              <div className="milestone-stat-divider" aria-hidden="true" />
              <div className="milestone-stat-item">
                <span className="milestone-stat-label">NEXT MILESTONE</span>
                <span className="milestone-stat-val">
                  {nextLevelNode ? `Level ${nextLevelNode.level} (${nextLevelNode.reqSolved - solvedCount} more needed)` : 'MAX LEVEL ACHIEVED'}
                </span>
              </div>
            </div>
          </div>

          <div className="milestone-hero-right">
            <div className="milestone-progress-info">
              <span>TIER PROGRESSION</span>
              <span>{progressToNext}%</span>
            </div>
            <div className="milestone-progress-bar" aria-label="Tier progress">
              <div
                className="milestone-progress-fill"
                style={{ width: `${progressToNext}%` }}
              />
            </div>
            <span className="milestone-progress-sub">
              {nextLevelNode
                ? `${solvedCount}/${nextLevelNode.reqSolved} challenges resolved to unlock ${nextLevelNode.title}`
                : 'All tree branches fully unlocked!'}
            </span>
          </div>
        </div>

        {/* Dual-Pane View: Left = Tree Roadmap, Right = Milestone Inspector */}
        <div className="milestone-workspace-layout">
          {/* LEFT: Tree Roadmap Canvas */}
          <div className="milestone-tree-panel">
            <div className="milestone-tree-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="file-dot" aria-hidden="true">●</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 700 }}>
                  [ SKILL TREE TOPOLOGY // 8 PROGRESSIVE TIERS ]
                </span>
              </div>
              <div className="milestone-tree-legend">
                <span className="legend-item"><span className="legend-dot legend-dot--completed" /> Completed</span>
                <span className="legend-item"><span className="legend-dot legend-dot--current" /> Current Level</span>
                <span className="legend-item"><span className="legend-dot legend-dot--locked" /> Locked</span>
              </div>
            </div>

            {/* Tree Roadmap Canvas */}
            <div className="milestone-tree-canvas">
              {/* TIER 5: APEX CROWN */}
              <div className="tree-tier tree-tier--apex">
                <div className="tree-tier-label">[ APEX TIER // 12 SOLVED ]</div>
                <div className="tree-tier-nodes">
                  {tier5Nodes.map((node) => (
                    <TreeNodeCard
                      key={node.id}
                      node={node}
                      state={getNodeState(node)}
                      isSelected={selectedNodeId === node.id}
                      onClick={() => setSelectedNodeId(node.id)}
                    />
                  ))}
                </div>
              </div>

              {/* Connecting Trunk Line */}
              <div className="tree-connector-v" />

              {/* TIER 4: HIGH COMPLEXITY CONVERGENCE */}
              <div className="tree-tier">
                <div className="tree-tier-label">[ MASTERY TIER // 10 SOLVED ]</div>
                <div className="tree-tier-nodes">
                  {tier4Nodes.map((node) => (
                    <TreeNodeCard
                      key={node.id}
                      node={node}
                      state={getNodeState(node)}
                      isSelected={selectedNodeId === node.id}
                      onClick={() => setSelectedNodeId(node.id)}
                    />
                  ))}
                </div>
              </div>

              {/* Fork Connectors */}
              <div className="tree-fork-connector">
                <div className="tree-fork-line tree-fork-line--left" />
                <div className="tree-fork-line tree-fork-line--right" />
              </div>

              {/* TIER 3: DUAL SPECIALIZATION BRANCHES */}
              <div className="tree-tier tree-tier--split">
                <div className="tree-tier-label">[ ADVANCED BRANCHES // 6 &amp; 8 SOLVED ]</div>
                <div className="tree-tier-nodes tree-tier-nodes--dual">
                  {tier3Nodes.map((node) => (
                    <TreeNodeCard
                      key={node.id}
                      node={node}
                      state={getNodeState(node)}
                      isSelected={selectedNodeId === node.id}
                      onClick={() => setSelectedNodeId(node.id)}
                    />
                  ))}
                </div>
              </div>

              {/* Join Connectors */}
              <div className="tree-join-connector">
                <div className="tree-join-line tree-join-line--left" />
                <div className="tree-join-line tree-join-line--right" />
              </div>

              {/* TIER 2: CORE JUNCTION */}
              <div className="tree-tier">
                <div className="tree-tier-label">[ CORE JUNCTION // 4 SOLVED ]</div>
                <div className="tree-tier-nodes">
                  {tier2Nodes.map((node) => (
                    <TreeNodeCard
                      key={node.id}
                      node={node}
                      state={getNodeState(node)}
                      isSelected={selectedNodeId === node.id}
                      onClick={() => setSelectedNodeId(node.id)}
                    />
                  ))}
                </div>
              </div>

              {/* Fork Connectors */}
              <div className="tree-fork-connector">
                <div className="tree-fork-line tree-fork-line--left" />
                <div className="tree-fork-line tree-fork-line--right" />
              </div>

              {/* TIER 1: EARLY FORK */}
              <div className="tree-tier tree-tier--split">
                <div className="tree-tier-label">[ FOUNDATIONAL DUAL PATHS // 1 &amp; 2 SOLVED ]</div>
                <div className="tree-tier-nodes tree-tier-nodes--dual">
                  {tier1Nodes.map((node) => (
                    <TreeNodeCard
                      key={node.id}
                      node={node}
                      state={getNodeState(node)}
                      isSelected={selectedNodeId === node.id}
                      onClick={() => setSelectedNodeId(node.id)}
                    />
                  ))}
                </div>
              </div>

              {/* Join Connectors */}
              <div className="tree-join-connector">
                <div className="tree-join-line tree-join-line--left" />
                <div className="tree-join-line tree-join-line--right" />
              </div>

              {/* TIER 0: ROOT / INITIATION */}
              <div className="tree-tier tree-tier--root">
                <div className="tree-tier-label">[ ROOT THRESHOLD // 0 SOLVED ]</div>
                <div className="tree-tier-nodes">
                  {tier0Nodes.map((node) => (
                    <TreeNodeCard
                      key={node.id}
                      node={node}
                      state={getNodeState(node)}
                      isSelected={selectedNodeId === node.id}
                      onClick={() => setSelectedNodeId(node.id)}
                    />
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* RIGHT: Selected Node Inspector Panel */}
          <div className="milestone-inspector-panel">
            <article className="schematic-card">
              <div className="schematic-card-header">
                <h2 className="schematic-card-header__title">
                  <span aria-hidden="true">▶</span> [ MILESTONE INSPECTOR ]
                </h2>
                <span className="schematic-card-header__tag">
                  {selectedNode.id === currentLevelNode.id
                    ? '[ YOUR CURRENT LEVEL ]'
                    : solvedCount >= selectedNode.reqSolved
                    ? '[ COMPLETED ]'
                    : '[ LOCKED ]'}
                </span>
              </div>

              <div className="milestone-inspector-body">
                {/* Node Identity */}
                <div className="inspector-node-hero">
                  <div className="inspector-node-icon" aria-hidden="true">
                    {selectedNode.icon}
                  </div>
                  <div>
                    <span className="inspector-node-level">LEVEL {selectedNode.level}</span>
                    <h3 className="inspector-node-title">{selectedNode.title}</h3>
                    <span className="inspector-node-subtitle">{selectedNode.subtitle}</span>
                  </div>
                </div>

                {/* Requirement Progress */}
                <div className="inspector-req-box">
                  <div className="inspector-req-header">
                    <span>UNLOCK REQUIREMENT:</span>
                    <strong>{selectedNode.reqSolved} SOLVED PROBLEMS</strong>
                  </div>
                  <div className="inspector-req-bar">
                    <div
                      className="inspector-req-fill"
                      style={{
                        width: `${Math.min(100, (solvedCount / Math.max(1, selectedNode.reqSolved)) * 100)}%`
                      }}
                    />
                  </div>
                  <div className="inspector-req-footer">
                    <span>Current Solved: {solvedCount}</span>
                    <span>
                      {solvedCount >= selectedNode.reqSolved
                        ? '✓ Unlocked'
                        : `${selectedNode.reqSolved - solvedCount} more needed`}
                    </span>
                  </div>
                </div>

                {/* Lore / Description */}
                <div className="schematic-param-box" style={{ margin: '14px 0 0' }}>
                  <span className="schematic-example-label">TECHNIQUE OVERVIEW:</span>
                  <p className="schematic-text" style={{ fontSize: '13px', margin: '4px 0 0', lineHeight: 1.6 }}>
                    {selectedNode.description}
                  </p>
                </div>

                {/* Unlocked Capabilities / Perks */}
                <div style={{ marginTop: '16px' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--color-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                    [ UNLOCKED CAPABILITIES ]
                  </span>
                  <ul className="inspector-perks-list">
                    {selectedNode.perks.map((perk, idx) => (
                      <li key={idx} className="inspector-perk-item">
                        <span className="perk-bullet" aria-hidden="true">◈</span>
                        <span>{perk}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Recommended Challenges to Advance */}
                {selectedNode.recommendedChallenges.length > 0 && (
                  <div style={{ marginTop: '16px' }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--color-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                      [ RECOMMENDED CHALLENGE VECTORS ]
                    </span>
                    <div className="inspector-challenges-list">
                      {selectedNode.recommendedChallenges.map((cid) => {
                        const ch = challenges.find((c) => c.id === cid) || { id: cid, title: cid, grade: 'Grade 4', difficulty: 'Easy' };
                        const isSolved = ch.status === 'Solved' || ch.status === 'passed';
                        return (
                          <div key={cid} className="inspector-challenge-row">
                            <div className="inspector-challenge-meta">
                              <span style={{ fontWeight: 600, color: '#FFFFFF', fontSize: '13px' }}>
                                {ch.title}
                              </span>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '3px' }}>
                                <GradeBadge grade={ch.grade} difficulty={ch.difficulty} />
                                {isSolved && (
                                  <span style={{ color: '#22c55e', fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
                                    ✓ Solved
                                  </span>
                                )}
                              </div>
                            </div>
                            <button
                              type="button"
                              className="secondary-btn"
                              style={{ padding: '6px 12px', fontSize: '11px' }}
                              onClick={() => onNavigate(`/challenges/${ch.id}`)}
                            >
                              {isSolved ? 'Review' : 'Attempt'} →
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            </article>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}

// Subcomponent: Individual Tree Node Card
function TreeNodeCard({ node, state, isSelected, onClick }) {
  const isCompleted = state === 'completed';
  const isCurrent = state === 'current';

  return (
    <button
      type="button"
      className={`tree-node-card tree-node-card--${state} ${isSelected ? 'tree-node-card--selected' : ''}`}
      onClick={onClick}
      aria-label={`Milestone Level ${node.level}: ${node.title}`}
    >
      <div className="tree-node-icon-box">
        <span className="tree-node-icon" aria-hidden="true">{node.icon}</span>
        {isCurrent && <span className="tree-node-pulse-ring" aria-hidden="true" />}
      </div>

      <div className="tree-node-info">
        <div className="tree-node-top">
          <span className="tree-node-level-tag">LVL {node.level}</span>
          <span className="tree-node-state-pill">
            {isCurrent ? 'CURRENT' : isCompleted ? '✓' : `🔒 ${node.reqSolved}`}
          </span>
        </div>
        <span className="tree-node-title">{node.title}</span>
        <span className="tree-node-req">
          {node.reqSolved === 0 ? 'Root' : `${node.reqSolved} Solved`}
        </span>
      </div>
    </button>
  );
}
