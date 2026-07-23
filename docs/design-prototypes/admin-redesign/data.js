// Shared fake dataset for the admin-panel redesign prototypes.
// Everything here is fictional. Shapes loosely mirror the real API payloads so
// the mockups stay honest about what data the backend can actually provide.
window.HUB = {
  today: '2026-07-23',

  levels: {
    introduction: { name: 'Introduction', color: '#941914' },
    explore:      { name: 'Explorer',     color: '#EF463C' },
    practitioner: { name: 'Practitioner', color: '#EE7684' },
    integrator:   { name: 'Integrator',   color: '#AB9BCB' },
    multiplier:   { name: 'Multiplier',   color: '#72C4BF' },
  },

  companies: [
    { id: 'c1', name: 'Nova Foods Group' },
    { id: 'c2', name: 'Veltman Logistics' },
    { id: 'c3', name: 'delaware BeLux' },
  ],

  projects: [
    {
      id: 'p1', companyId: 'c1', name: 'AI Foundations — Wave 1', created: '12 May 2026',
      funnel: { invited: 12, activated: 10, assessed: 9, learning: 8, completedTrack: 3 },
      maturity: { explore: 4, practitioner: 3, integrator: 2 },
      openFeedback: 4, stuck: 4, activeThisWeek: 6, avgCompletion: 46,
      components: [
        { key: 'assessment', label: 'Assessment',    visible: true,  locked: false },
        { key: 'learning',   label: 'Learning path', visible: true,  locked: false },
        { key: 'interview',  label: 'Interview',     visible: false, locked: true  },
      ],
      defaults: { 't-intro': true, 't-gen1': true, 't-gen2': true, 't-copilot': true, 't-claude': false, 't-obsidian': false },
    },
    {
      id: 'p2', companyId: 'c2', name: 'AI Enablement Pilot', created: '2 Jun 2026',
      funnel: { invited: 8, activated: 7, assessed: 5, learning: 5, completedTrack: 1 },
      maturity: { explore: 3, practitioner: 2, integrator: 0 },
      openFeedback: 1, stuck: 2, activeThisWeek: 4, avgCompletion: 28,
      components: [
        { key: 'assessment', label: 'Assessment',    visible: true,  locked: false },
        { key: 'learning',   label: 'Learning path', visible: true,  locked: true  },
        { key: 'interview',  label: 'Interview',     visible: false, locked: true  },
      ],
      defaults: { 't-intro': true, 't-gen1': true, 't-gen2': false, 't-copilot': false, 't-claude': false, 't-obsidian': false },
    },
    {
      id: 'p3', companyId: 'c3', name: 'FDE Upskilling', created: '20 Apr 2026',
      funnel: { invited: 7, activated: 7, assessed: 7, learning: 6, completedTrack: 4 },
      maturity: { explore: 1, practitioner: 3, integrator: 3 },
      openFeedback: 0, stuck: 0, activeThisWeek: 4, avgCompletion: 71,
      components: [
        { key: 'assessment', label: 'Assessment',    visible: true,  locked: false },
        { key: 'learning',   label: 'Learning path', visible: true,  locked: false },
        { key: 'interview',  label: 'Interview',     visible: true,  locked: false },
      ],
      defaults: { 't-intro': true, 't-gen1': true, 't-gen2': true, 't-copilot': true, 't-claude': true, 't-obsidian': true },
    },
  ],

  tracks: [
    { id: 't-intro', name: 'Introduction', level: 'introduction', modules: [
      { id: 'in-welcome', name: 'Welcome', lessons: [{ id: 'in-w1', name: 'Why this journey' }, { id: 'in-w2', name: 'How the hub works' }] },
      { id: 'in-journey', name: 'Your journey', lessons: [{ id: 'in-j1', name: 'The maturity ladder' }, { id: 'in-j2', name: 'Your assessment' }] },
    ]},
    { id: 't-gen1', name: 'General I', level: 'explore', modules: [
      { id: 'g1-what', name: 'What AI is', lessons: [
        { id: 'g1-w1', name: 'Meet your new colleague' }, { id: 'g1-w2', name: 'Beyond chat' }, { id: 'g1-w3', name: 'What it can and cannot do' }] },
      { id: 'g1-how', name: 'How AI works', lessons: [
        { id: 'g1-h1', name: 'Tokens and predictions' }, { id: 'g1-h2', name: 'Why it makes things up' }] },
      { id: 'g1-prompt', name: 'Prompting', lessons: [
        { id: 'g1-p1', name: 'Anatomy of a good prompt' }, { id: 'g1-p2', name: 'Prompt patterns' }, { id: 'g1-p3', name: 'Iterating on results' }] },
      { id: 'g1-safety', name: 'Safety', lessons: [
        { id: 'g1-s1', name: 'Using AI responsibly' }, { id: 'g1-s2', name: 'What not to share' }] },
    ]},
    { id: 't-gen2', name: 'General II', level: 'practitioner', modules: [
      { id: 'g2-ctx', name: 'Context & grounding', lessons: [
        { id: 'g2-c1', name: 'Give it your context' }, { id: 'g2-c2', name: 'Working with documents' }] },
      { id: 'g2-rev', name: 'Reviewing output', lessons: [
        { id: 'g2-r1', name: 'Review rituals' }, { id: 'g2-r2', name: 'Spotting hallucinations' }] },
      { id: 'g2-flow', name: 'Daily workflows', lessons: [
        { id: 'g2-f1', name: 'Recurring tasks with AI' }, { id: 'g2-f2', name: 'Build your prompt library' }] },
    ]},
    { id: 't-copilot', name: 'Copilot', level: 'practitioner', modules: [
      { id: 'cp-start', name: 'Get started', lessons: [
        { id: 'cp-s1', name: 'Copilot in your apps' }, { id: 'cp-s2', name: 'Chat vs in-app' }, { id: 'cp-s3', name: 'Module quiz' }] },
      { id: 'cp-ground', name: 'Ground it', lessons: [
        { id: 'cp-g1', name: 'Grounding in your own data' }, { id: 'cp-g2', name: 'Referencing files & people' }, { id: 'cp-g3', name: 'Personalizing Copilot' }] },
      { id: 'cp-cowork', name: 'Cowork', lessons: [
        { id: 'cp-c1', name: 'What Cowork is' }, { id: 'cp-c2', name: 'Working with Cowork' }, { id: 'cp-c3', name: 'Connecting Cowork' }] },
      { id: 'cp-cap', name: 'Capstone', lessons: [
        { id: 'cp-x1', name: 'Your Copilot workflow' }] },
    ]},
    { id: 't-claude', name: 'Claude', level: 'integrator', modules: [
      { id: 'cl-start', name: 'Get started', lessons: [
        { id: 'cl-s1', name: 'Meet Claude' }, { id: 'cl-s2', name: 'Artifacts' }] },
      { id: 'cl-proj', name: 'Projects', lessons: [
        { id: 'cl-p1', name: 'Working in Projects' }, { id: 'cl-p2', name: 'Project knowledge' }] },
      { id: 'cl-cap', name: 'Capstone', lessons: [
        { id: 'cl-x1', name: 'Your Claude workflow' }] },
    ]},
    { id: 't-obsidian', name: 'Obsidian', level: 'integrator', modules: [
      { id: 'ob-start', name: 'Get started', lessons: [
        { id: 'ob-s1', name: 'Your vault' }, { id: 'ob-s2', name: 'Notes & links' }] },
      { id: 'ob-use', name: 'Use it well', lessons: [
        { id: 'ob-u1', name: 'Daily notes' }, { id: 'ob-u2', name: 'Linking your thinking' }] },
      { id: 'ob-cap', name: 'Capstone', lessons: [
        { id: 'ob-x1', name: 'Build your second brain' }] },
    ]},
  ],

  // status: active | invited   flags: stalled | never-started | assessment-pending
  // assign values per track: 'def' inherited from project default, 'yes' explicit,
  // 'part' partial, '' not assigned. For 'part' tracks, assignModules holds the
  // per-module states; for 'part' modules, assignLessons holds per-lesson states.
  users: [
    { id: 'u01', projectId: 'p1', name: 'Lotte Peeters',    email: 'lotte.peeters@novafoods.example',    status: 'active',  role: 'user',  level: 'practitioner', progress: 62, lastActive: 1,  flags: [],
      assign: { 't-intro': 'def', 't-gen1': 'def', 't-gen2': 'def', 't-copilot': 'def', 't-claude': '', 't-obsidian': '' },
      trackProgress: { 't-intro': 100, 't-gen1': 85, 't-gen2': 45, 't-copilot': 30 },
      survey: {
        completed: '18 May 2026', level: 'practitioner', band: 'regular', safety: 'No safety concerns flagged',
        competencies: [
          { q: 'Understanding what AI can and cannot do', a: 'I can explain the basics and spot obvious limitations', rung: 2 },
          { q: 'Prompting', a: 'I write multi-part prompts with context and examples', rung: 2 },
          { q: 'Reviewing AI output', a: 'I sometimes check facts when it matters', rung: 1 },
          { q: 'Integrating AI in my workflow', a: 'I use AI for recurring tasks in my own work', rung: 2 },
          { q: 'Building & automating with AI', a: "I haven't built anything with AI yet", rung: 0 },
        ],
        usage: { frequency: 'A few times a week', tools: ['Microsoft Copilot', 'ChatGPT'], contexts: ['Writing & rewriting', 'Summarizing documents', 'Excel formulas'] },
        open: [
          { q: 'Where would AI help you most?', a: 'Preparing customer meeting summaries — collecting inputs from mails and notes takes me hours every week.' },
          { q: 'What is your biggest concern using AI at work?', a: 'Sharing something confidential without realizing it.' },
        ],
      } },
    { id: 'u02', projectId: 'p1', name: 'Jonas Vermeulen',  email: 'jonas.vermeulen@novafoods.example',  status: 'active',  role: 'user+', level: 'integrator',   progress: 84, lastActive: 0,  flags: [],
      assign: { 't-intro': 'def', 't-gen1': 'def', 't-gen2': 'def', 't-copilot': 'def', 't-claude': 'yes', 't-obsidian': 'part' },
      assignModules: { 't-obsidian': { 'ob-start': 'yes', 'ob-use': '', 'ob-cap': '' } } },
    { id: 'u03', projectId: 'p1', name: 'Sofie De Smet',    email: 'sofie.desmet@novafoods.example',     status: 'active',  role: 'user',  level: 'practitioner', progress: 55, lastActive: 2,  flags: [],
      assign: { 't-intro': 'def', 't-gen1': 'def', 't-gen2': 'def', 't-copilot': 'def', 't-claude': '', 't-obsidian': '' } },
    { id: 'u04', projectId: 'p1', name: 'Arno Claes',       email: 'arno.claes@novafoods.example',       status: 'invited', role: 'user',  level: null,           progress: 0,  lastActive: null, flags: ['never-started'],
      assign: { 't-intro': 'def', 't-gen1': 'def', 't-gen2': 'def', 't-copilot': 'def', 't-claude': '', 't-obsidian': '' } },
    { id: 'u05', projectId: 'p1', name: 'Marieke Janssens', email: 'marieke.janssens@novafoods.example', status: 'active',  role: 'user',  level: 'explore',      progress: 38, lastActive: 3,  flags: [],
      assign: { 't-intro': 'def', 't-gen1': 'def', 't-gen2': 'def', 't-copilot': 'def', 't-claude': '', 't-obsidian': '' } },
    { id: 'u06', projectId: 'p1', name: 'Thomas Van Damme', email: 'thomas.vandamme@novafoods.example',  status: 'active',  role: 'user',  level: 'practitioner', progress: 47, lastActive: 16, flags: ['stalled'], stallNote: 'Stalled in Copilot › Cowork for 16 days',
      assign: { 't-intro': 'def', 't-gen1': 'def', 't-gen2': 'def', 't-copilot': 'def', 't-claude': '', 't-obsidian': '' } },
    { id: 'u07', projectId: 'p1', name: 'Elke Maes',        email: 'elke.maes@novafoods.example',        status: 'active',  role: 'user',  level: 'explore',      progress: 21, lastActive: 21, flags: ['stalled'], stallNote: 'Stalled in General I › Safety for 21 days',
      assign: { 't-intro': 'def', 't-gen1': 'def', 't-gen2': 'def', 't-copilot': 'def', 't-claude': '', 't-obsidian': '' } },
    { id: 'u08', projectId: 'p1', name: 'Ruben De Vos',     email: 'ruben.devos@novafoods.example',      status: 'active',  role: 'user',  level: 'integrator',   progress: 91, lastActive: 1,  flags: [],
      assign: { 't-intro': 'def', 't-gen1': 'def', 't-gen2': 'def', 't-copilot': 'def', 't-claude': 'yes', 't-obsidian': 'yes' } },
    { id: 'u09', projectId: 'p1', name: 'Hanne Willems',    email: 'hanne.willems@novafoods.example',    status: 'active',  role: 'user',  level: null,           progress: 0,  lastActive: 8,  flags: ['assessment-pending'], stallNote: 'Activated 8 days ago, assessment not started',
      assign: { 't-intro': 'def', 't-gen1': 'def', 't-gen2': 'def', 't-copilot': 'def', 't-claude': '', 't-obsidian': '' } },
    { id: 'u10', projectId: 'p1', name: 'Pieter Goossens',  email: 'pieter.goossens@novafoods.example',  status: 'active',  role: 'user',  level: 'explore',      progress: 33, lastActive: 5,  flags: [],
      assign: { 't-intro': 'def', 't-gen1': 'def', 't-gen2': 'def', 't-copilot': 'part', 't-claude': '', 't-obsidian': '' },
      assignModules: { 't-copilot': { 'cp-start': 'yes', 'cp-ground': 'part', 'cp-cowork': '', 'cp-cap': '' } },
      assignLessons: { 'cp-ground': { 'cp-g1': 'yes', 'cp-g2': 'yes', 'cp-g3': '' } } },
    { id: 'u11', projectId: 'p1', name: 'Laura Michiels',   email: 'laura.michiels@novafoods.example',   status: 'active',  role: 'user',  level: 'practitioner', progress: 58, lastActive: 2,  flags: [],
      assign: { 't-intro': 'def', 't-gen1': 'def', 't-gen2': 'def', 't-copilot': 'def', 't-claude': 'yes', 't-obsidian': '' } },
    { id: 'u12', projectId: 'p1', name: 'Bram Verhoeven',   email: 'bram.verhoeven@novafoods.example',   status: 'invited', role: 'user',  level: null,           progress: 0,  lastActive: null, flags: ['never-started'],
      assign: { 't-intro': 'def', 't-gen1': 'def', 't-gen2': 'def', 't-copilot': 'def', 't-claude': '', 't-obsidian': '' } },

    { id: 'u13', projectId: 'p2', name: 'Nele Jacobs',      email: 'nele.jacobs@veltman.example',        status: 'active',  role: 'user',  level: 'explore',      progress: 42, lastActive: 1,  flags: [] ,
      assign: { 't-intro': 'def', 't-gen1': 'def', 't-gen2': '', 't-copilot': '', 't-claude': '', 't-obsidian': '' } },
    { id: 'u14', projectId: 'p2', name: 'Simon Peers',      email: 'simon.peers@veltman.example',        status: 'active',  role: 'user',  level: 'practitioner', progress: 51, lastActive: 4,  flags: [],
      assign: { 't-intro': 'def', 't-gen1': 'def', 't-gen2': 'yes', 't-copilot': 'yes', 't-claude': '', 't-obsidian': '' } },
    { id: 'u15', projectId: 'p2', name: 'Astrid Mertens',   email: 'astrid.mertens@veltman.example',     status: 'active',  role: 'user',  level: 'explore',      progress: 12, lastActive: 14, flags: ['stalled'], stallNote: 'Stalled in General I › What AI is for 14 days',
      assign: { 't-intro': 'def', 't-gen1': 'def', 't-gen2': '', 't-copilot': '', 't-claude': '', 't-obsidian': '' } },
    { id: 'u16', projectId: 'p2', name: 'Koen Wouters',     email: 'koen.wouters@veltman.example',       status: 'invited', role: 'user',  level: null,           progress: 0,  lastActive: null, flags: ['never-started'],
      assign: { 't-intro': 'def', 't-gen1': 'def', 't-gen2': '', 't-copilot': '', 't-claude': '', 't-obsidian': '' } },
    { id: 'u17', projectId: 'p2', name: 'Femke Segers',     email: 'femke.segers@veltman.example',       status: 'active',  role: 'user',  level: 'practitioner', progress: 36, lastActive: 2,  flags: [],
      assign: { 't-intro': 'def', 't-gen1': 'def', 't-gen2': 'yes', 't-copilot': '', 't-claude': '', 't-obsidian': '' } },

    { id: 'u18', projectId: 'p3', name: 'Matthias D.',      email: 'matthias@delaware.example',          status: 'active',  role: 'admin', level: 'integrator',   progress: 88, lastActive: 0,  flags: [],
      assign: { 't-intro': 'def', 't-gen1': 'def', 't-gen2': 'def', 't-copilot': 'def', 't-claude': 'def', 't-obsidian': 'def' } },
    { id: 'u19', projectId: 'p3', name: 'Aaron N.',         email: 'aaron@delaware.example',             status: 'active',  role: 'admin', level: 'integrator',   progress: 76, lastActive: 0,  flags: [],
      assign: { 't-intro': 'def', 't-gen1': 'def', 't-gen2': 'def', 't-copilot': 'def', 't-claude': 'def', 't-obsidian': 'def' } },
    { id: 'u20', projectId: 'p3', name: 'Charlotte Baert',  email: 'charlotte.baert@delaware.example',   status: 'active',  role: 'user+', level: 'practitioner', progress: 64, lastActive: 1,  flags: [],
      assign: { 't-intro': 'def', 't-gen1': 'def', 't-gen2': 'def', 't-copilot': 'def', 't-claude': 'def', 't-obsidian': 'def' } },
  ],

  // loc = structured location (track/module/lesson) so the queue can filter
  // and slice on it — mirrors what a lesson_id join gives the real backend.
  feedback: [
    { id: 'f1', projectId: 'p1', user: 'Sofie De Smet',   date: '22 Jul', type: 'Content error',
      loc: { track: 't-copilot', module: 'cp-ground', lesson: 'cp-g1' },
      quote: 'The lesson says Copilot can read any SharePoint site, but in our tenant it only sees sites I follow — maybe worth clarifying.',
      ai: { feasibility: 'High', effort: 'Low', note: 'Single-paragraph clarification, no structural change.' }, status: 'new' },
    { id: 'f2', projectId: 'p1', user: 'Jonas Vermeulen', date: '21 Jul', type: 'Suggestion',
      loc: { track: 't-gen1', module: 'g1-prompt', lesson: 'g1-p2' },
      quote: 'Would love a downloadable cheat sheet of the prompt patterns at the end of the module.',
      ai: { feasibility: 'High', effort: 'Medium', note: 'New asset + link block; source content already exists in the lesson.' }, status: 'new' },
    { id: 'f3', projectId: 'p1', user: 'Laura Michiels',  date: '20 Jul', type: 'Unclear',
      loc: { track: 't-claude', module: 'cl-proj', lesson: 'cl-p1' },
      quote: 'The difference between Projects and regular chats only became clear to me at the capstone.',
      ai: { feasibility: 'Medium', effort: 'Medium', note: 'Needs a comparison table early in the module; touches two lessons.' }, status: 'new' },
    { id: 'f4', projectId: 'p1', user: 'Pieter Goossens', date: '19 Jul', type: 'Content error',
      loc: { track: 't-copilot', module: 'cp-start', lesson: 'cp-s3' },
      quote: 'Question 3 marks what I believe is the correct answer as wrong.',
      ai: { feasibility: 'High', effort: 'Low', note: 'Verify answer key; likely a key-name mismatch in the quiz block.' }, status: 'new' },
    { id: 'f5', projectId: 'p2', user: 'Simon Peers',     date: '18 Jul', type: 'Suggestion',
      loc: { track: 't-obsidian', module: 'ob-cap', lesson: 'ob-x1' },
      quote: 'The capstone assumes I finished the linking section, but earlier it is marked optional.',
      ai: { feasibility: 'High', effort: 'Low', note: 'Reword the prerequisite note in the capstone intro.' }, status: 'new' },
    { id: 'f6', projectId: 'p1', user: 'Marieke Janssens', date: '15 Jul', type: 'Suggestion',
      loc: { track: 't-gen2', module: 'g2-rev', lesson: 'g2-r1' },
      quote: 'Could you add an example for reviewing legal documents?',
      ai: { feasibility: 'Medium', effort: 'Medium', note: 'One new worked example; needs SME input for the legal angle.' }, status: 'accepted' },
    { id: 'f7', projectId: 'p2', user: 'Astrid Mertens',  date: '12 Jul', type: 'Unclear',
      loc: { track: 't-gen1', module: 'g1-safety', lesson: 'g1-s1' },
      quote: 'Too long.',
      ai: { feasibility: 'Low', effort: 'High', note: 'Vague signal; module length is a deliberate design choice.' }, status: 'dismissed' },
  ],
}
