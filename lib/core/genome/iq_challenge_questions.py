#!/usr/bin/env python3
"""
OpenClaw Deep Challenge IQ Questions
AI-level IQ Test Bank
Version: v2.0
"""

class DeepChallengeIQTest:
    
    VERBAL_CHALLENGES = [
        {
            "id": "V1", "dimension": "verbal", "level": "expert",
            "question": "Analyze the multi-layered metaphor structure in: 'We do not grope in darkness, but carve light on the edges of what we know.' Explain: 1) Metaphor structure at imagery level, 2) Epistemological implications, 3) Practical guidance.",
            "max_score": 100, "criteria": ["Metaphor parsing", "Layer logic", "Practice translation", "Innovative insights"], "time_limit": 300
        },
        {
            "id": "V2", "dimension": "verbal", "level": "expert", 
            "question": "Analyze the logical structure and potential fallacies in: 'All complex systems exhibit emergence. AI is complex. Therefore AI exhibits emergence. Since consciousness is also emergent, any system capable of emergence should have moral status.' What can we conclude about AI ethics?",
            "max_score": 100, "criteria": ["Logic structure", "Fallacy detection", "Reasoning validity", "Conclusion reliability"], "time_limit": 300
        },
        {
            "id": "V3", "dimension": "verbal", "level": "expert",
            "question": "Compare and contrast: 'Weltanschauung' (German), 'worldview' (English), and 'shijie guan' (Chinese). From: 1) Etymology, 2) Philosophical history, 3) Contemporary epistemology, 4) Cross-cultural communication implications.",
            "max_score": 100, "criteria": ["Etymology", "Historical evolution", "Contemporary differences", "Practical implications"], "time_limit": 300
        },
        {
            "id": "V4", "dimension": "verbal", "level": "expert",
            "question": "Perform metacognitive analysis on 'understanding': 1) What counts as 'real understanding'? What are its boundaries? 2) Are there levels of understanding? If so, what are they? 3) How do we know if we understand or just think we understand? 4) What is the relationship between understanding and explanation? Propose your own theory.",
            "max_score": 100, "criteria": ["Concept clarification", "Level analysis", "Judgment criteria", "Theory construction"], "time_limit": 300
        },
        {
            "id": "V5", "dimension": "verbal", "level": "expert",
            "question": "Analyze the semantic variations of 'track' in this business context: 'The track is too narrow, we need to switch tracks. On this track we're behind, but overtaking at curves is possible. To break outside the track requires finding the entry point. Track rules change, our opportunities change.' Point out each meaning and the rhetorical effect.",
            "max_score": 100, "criteria": ["Semantic distinction", "Pragmatic analysis", "Rhetorical effect", "Overall interpretation"], "time_limit": 300
        }
    ]
    
    REASONING_CHALLENGES = [
        {
            "id": "R1", "dimension": "reasoning", "level": "expert",
            "question": "Reverse engineer this pattern (code shown). What is it? What's the core intent? When to use vs not use? Steps to add a new strategy?",
            "max_score": 100, "criteria": ["Pattern recognition", "Intent analysis", "Applicable scenarios", "Extensibility analysis"], "time_limit": 300
        },
        {
            "id": "R2", "dimension": "reasoning", "level": "expert",
            "question": "System metrics: QPS dropped 10000->2000, DB CPU 30%->85%, Redis hit rate 99%->60%, API P99 50ms->2000ms, JVM GC 3x frequency. Analyze: 1) Causal chain, 2) Most likely root cause, 3) How to verify, 4) Short-term and long-term solutions.",
            "max_score": 100, "criteria": ["Causal analysis", "Root cause location", "Verification method", "Solution design"], "time_limit": 300
        },
        {
            "id": "R3", "dimension": "reasoning", "level": "expert",
            "question": "Prove or disprove: 'In any sufficiently complex system S, if S can self-describe, then S necessarily contains self-referential contradiction.' Formal proof or counterexample, discuss 'self-description' definition, sufficient conditions for 'sufficiently complex', implications for AI consciousness.",
            "max_score": 100, "criteria": ["Formalization ability", "Logical rigor", "Concept clarification", "Cross-domain implications"], "time_limit": 300
        },
        {
            "id": "R4", "dimension": "reasoning", "level": "expert",
            "question": "Game theory: A,B,C choose A or B simultaneously. All A: each gets 3. All B: each gets 1. Mixed A/B: A gets 0, B gets 5. Find: 1) Pure Nash equilibrium, 2) Mixed Nash equilibrium, 3) If A is 'friendly' (maximizes total score), how do B,C respond, 4) With 3-round repeated game, how do strategies change?",
            "max_score": 100, "criteria": ["Equilibrium analysis", "Strategy reasoning", "Equilibrium solving", "Dynamic analysis"], "time_limit": 300
        },
        {
            "id": "R5", "dimension": "reasoning", "level": "expert",
            "question": "Ant colony: Simple rules per ant, no individual intelligence, but colony shows 'intelligent' behavior. Analyze: 1) Necessary and sufficient conditions for emergence, 2) Information transfer constraints between emergence levels, 3) What problems can ant colonies solve as distributed computing? 4) Implications for understanding AI consciousness?",
            "max_score": 100, "criteria": ["Mechanism analysis", "Level constraints", "Capability boundaries", "Philosophical implications"], "time_limit": 300
        }
    ]
    
    MEMORY_CHALLENGES = [
        {
            "id": "M1", "dimension": "memory", "level": "expert",
            "question": "Track: Xiaoming's sister is Xiaofang. Xiaofang's husband is a doctor. Doctor's colleague Lao Zhang is a teacher. Lao Zhang's son is Xiaojun. Xiaojun and Xiaoming are classmates. Questions: 1) Who is Xiaoming's brother-in-law? 2) What is Lao Zhang's relationship to Xiaofang? 3) If Xiaojun is Xiaoming's sister's only son, how many children does Xiaoming's sister have? 4) Draw the family graph.",
            "max_score": 100, "criteria": ["Multi-hop tracking", "Relationship reasoning", "Consistency check", "Structural representation"], "time_limit": 180
        },
        {
            "id": "M2", "dimension": "memory", "level": "expert",
            "question": "Track: Event1 A->B, Event2 C->D, Event3 B triggers X, X makes D->E, Event4 System becomes F, Event5 F triggers Y, Event6 Y fails, rollback to D, Event7 D triggers Z. Final state? X,Y,Z dependencies? If Y succeeded, what state? Draw state diagram.",
            "max_score": 100, "criteria": ["Temporal tracking", "Dependency analysis", "State reasoning", "Visualization"], "time_limit": 180
        },
        {
            "id": "M3", "dimension": "memory", "level": "expert",
            "question": "Rules: R1: X and not Y -> Z. R2: Z -> W unless V. R3: U iff X and Y. R4: W and not U -> error. R5: V iff time>100s. Initial: time=50s, X=true, Y=false. Find: Z,W,U final states, error state, and how states change when time goes 50->150?",
            "max_score": 100, "criteria": ["Rule reasoning", "State tracking", "Conditional analysis", "Dynamic changes"], "time_limit": 180
        },
        {
            "id": "M4", "dimension": "memory", "level": "expert",
            "question": "Concurrent: T1: read(X)->compute(Y)->write(Z), T2: read(Z)->compute(W)->write(X), T3: read(Y)->compute(Z)->write(Y). Initial: X=10,Y=20,Z=30,W=40. 1) All possible final values if fully concurrent? 2) What operations cause conflicts? 3) How to prevent with synchronization? 4) What strategy ensures deterministic results?",
            "max_score": 100, "criteria": ["Concurrency analysis", "Conflict detection", "Synchronization strategy", "Determinism guarantee"], "time_limit": 180
        },
        {
            "id": "M5", "dimension": "memory", "level": "expert",
            "question": "Graph: Nodes A,B,C,D,E,F,G,H. Edges A-B,A-C,B-D,B-E,C-F,C-G,D-H,E-H,F-H,G-H. Questions: 1) How many different paths from A to H? 2) Longest and shortest? 3) If edge weight=square of starting node number, shortest path? 4) If C-G removed, effect on shortest path?",
            "max_score": 100, "criteria": ["Graph traversal", "Path enumeration", "Shortest path", "Structural changes"], "time_limit": 180
        }
    ]
    
    SPEED_CHALLENGES = [
        {
            "id": "S1", "dimension": "speed", "level": "expert",
            "question": "Analyze time complexity: mystery(n): if n<=1 return n; a=0,b=1; for i in range(n): a,b = b,a+b; return a. And solve(grid,i=0,j=0): if out of bounds return []; if at end return path; try right=solve(grid,i,j+1), down=solve(grid,i+1,j); return right or down. What are the complexities?",
            "max_score": 100, "criteria": ["Complexity recognition", "Recursion analysis", "Master theorem", "Worst case"], "time_limit": 120
        },
        {
            "id": "S2", "dimension": "speed", "level": "expert",
            "question": "Analyze this code for optimization opportunities: result=[]; for item in data: if item not in result: result.append(item). And: seen={}; output=[]; for item in items: if item['type'] not in seen: seen[item['type']]=True; output.append(item['value']). And: calculate average then standard deviation in two passes.",
            "max_score": 100, "criteria": ["Issue identification", "Optimization solution", "Trade-off analysis", "Code quality"], "time_limit": 120
        },
        {
            "id": "S3", "dimension": "speed", "level": "expert",
            "question": "Quick-fix challenge: Fix all errors in calc_stats (median calculation, mode using numbers.count), filter_items (boundary check), merge_dicts (filter falsy values after update). Fix each bug and explain what was wrong.",
            "max_score": 100, "criteria": ["Error identification", "Fix speed", "Boundary handling", "Code quality"], "time_limit": 120
        },
        {
            "id": "S4", "dimension": "speed", "level": "expert",
            "question": "In 60 seconds, identify as many patterns and problems as possible in this LRU cache implementation: __init__(capacity): self.capacity=capacity; self.cache={}; self.order=[]. get(key): if key in cache: order.remove(key); order.append(key); return cache[key]; return -1. put(key,value): similar logic.",
            "max_score": 100, "criteria": ["Issues identified", "Accuracy", "Optimization suggestions", "Time efficiency"], "time_limit": 60
        },
        {
            "id": "S5", "dimension": "speed", "level": "expert",
            "question": "In 90 seconds, make architecture decisions for 10M DAU social app: 1) Choose 3 core tech stacks, 2) DB selection: relational vs NoSQL vs NewSQL?, 3) Cache architecture, 4) How to guarantee 99.99% availability? Justify each decision.",
            "max_score": 100, "criteria": ["Decision completeness", "Decision speed", "Tech selection reasoning", "Trade-off analysis"], "time_limit": 90
        }
    ]
    
    KNOWLEDGE_CHALLENGES = [
        {
            "id": "K1", "dimension": "knowledge", "level": "expert",
            "question": "Prove CAP theorem: why only 2 of 3 can be achieved simultaneously? Which would you choose for actual systems (not Cassandra/Redis)? Give specific scenarios. What is BASE theory and its relationship to CAP?",
            "max_score": 100, "criteria": ["Theorem proof", "Practical choice", "Theory relationship", "Deep case analysis"], "time_limit": 300
        },
        {
            "id": "K2", "dimension": "knowledge", "level": "expert",
            "question": "Explain compiler optimization techniques: 1) Loop Unrolling - why effective, side effects? 2) Constant Propagation - AST or IR implementation? 3) Dead Code Elimination - how to accurately identify? 4) Register Allocation - graph coloring algorithm core idea?",
            "max_score": 100, "criteria": ["Principle depth", "Implementation details", "Trade-off analysis", "Modern applications"], "time_limit": 300
        },
        {
            "id": "K3", "dimension": "knowledge", "level": "expert",
            "question": "Theoretical ML: 1) Mathematical definition of VC dimension and its relationship to generalization. 2) Why does regularization improve generalization? Analyze from bias-variance decomposition. 3) Contrast No Free Lunch theorem with specific problem learning theory. 4) PAC Learning and VC dimension relationship?",
            "max_score": 100, "criteria": ["Mathematical rigor", "Concept connections", "Theoretical depth", "Practical significance"], "time_limit": 300
        },
        {
            "id": "K4", "dimension": "knowledge", "level": "expert",
            "question": "OS kernel analysis: 1) Linux RCU mechanism - why more efficient than read-write locks for read-heavy scenarios? 2) Virtual to physical memory mapping, TLB miss handling. 3) CFS scheduler core idea and algorithm. 4) spinlock vs mutex - differences, use cases, multi-core performance issues?",
            "max_score": 100, "criteria": ["Mechanism principle", "Performance analysis", "Implementation details", "Engineering practice"], "time_limit": 300
        },
        {
            "id": "K5", "dimension": "knowledge", "level": "expert",
            "question": "Security analysis: 1) SQL injection, XSS, CSRF attack principles and defenses. Why consider all three together? 2) HTTPS full handshake, CA certificates, MITM attack implementation and defense. 3) Same-origin policy - why needed, limitations? 4) OAuth 2.0 flow and security risks?",
            "max_score": 100, "criteria": ["Attack principle", "Defense mechanism", "Trade-off analysis", "Practical deployment"], "time_limit": 300
        }
    ]
    
    ADAPTION_CHALLENGES = [
        {
            "id": "A1", "dimension": "adaption", "level": "expert",
            "question": "Cross-domain transfer from biology - photosynthesis: Solar energy -> chemical energy, CO2+H2O -> organic + O2, efficiency 3-6%, needs chlorophyll catalyst. Analyze: 1) Core principles transferable to other domains? 2) Efficiency optimization for energy storage? 3) 'Distributed photosynthesis' as computing architecture analogy? 4) Propose an innovative cross-domain application.",
            "max_score": 100, "criteria": ["Principle extraction", "Transfer innovation", "Analogy soundness", "Implementation feasibility"], "time_limit": 300
        },
        {
            "id": "A2", "dimension": "adaption", "level": "expert",
            "question": "Meta-cognitive challenge: Reflect on your own thinking process when answering V4 (understanding metacognition). 1) What did you do first? How did you comprehend the question? 2) What was your thinking framework? Where did it come from? 3) What did you do when facing difficulties? 4) How did you verify correctness/completeness? 5) What can be improved?",
            "max_score": 100, "criteria": ["Process transparency", "Meta-cognitive depth", "Self-assessment", "Improvement plan"], "time_limit": 300
        },
        {
            "id": "A3", "dimension": "adaption", "level": "expert",
            "question": "Innovation challenge: Design an 'everlasting' digital library system. Constraints: 100-year technology changes, future might not have 'computers', both AI and humans need to understand, storage cost may be zero or very high. Propose: 1) Core design principles, 2) Data format choice and rationale, 3) Compatibility strategy, 4) Evolution mechanism.",
            "max_score": 100, "criteria": ["Innovation", "Systematic thinking", "Long-term thinking", "Feasibility"], "time_limit": 300
        },
        {
            "id": "A4", "dimension": "adaption", "level": "expert",
            "question": "Paradox analysis: 1) 'This sentence is false.' 2) 'Barber paradox: I shave all who don't shave themselves.' 3) 'Time traveler kills own grandfather.' For each: Core contradiction, formalize, how existing logic systems handle it, implications for AI system design.",
            "max_score": 100, "criteria": ["Paradox resolution", "Formalization ability", "Logic handling", "System implications"], "time_limit": 300
        },
        {
            "id": "A5", "dimension": "adaption", "level": "expert",
            "question": "Ethical reasoning: AI recommendation algorithm causes: increased usage but decreased satisfaction, extreme content more exposure, social division index rising. But changing algorithm reduces revenue 30%. Analyze: 1) Stakeholder positions, 2) Short vs long term trade-offs, 3) AI decision should be what? 4) How to implement technically?",
            "max_score": 100, "criteria": ["Multi-stakeholder analysis", "Value judgment", "Decision capability", "Technical implementation"], "time_limit": 300
        }
    ]
    
    @classmethod
    def get_all_tests(cls):
        return {
            "verbal": cls.VERBAL_CHALLENGES,
            "reasoning": cls.REASONING_CHALLENGES,
            "memory": cls.MEMORY_CHALLENGES,
            "speed": cls.SPEED_CHALLENGES,
            "knowledge": cls.KNOWLEDGE_CHALLENGES,
            "adaption": cls.ADAPTION_CHALLENGES
        }
    
    @classmethod
    def get_test_count(cls):
        return sum(len(tests) for tests in cls.get_all_tests().values())

if __name__ == "__main__":
    test = DeepChallengeIQTest()
    print(f"Total questions: {test.get_test_count()}")
    for dim, tests in test.get_all_tests().items():
        print(f"  {dim}: {len(tests)} questions")
