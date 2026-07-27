// frontend/src/pages/DevChat.tsx
//
// TEMPORARY Batch A verification harness for the AI chat foundation. This page is a
// throwaway dev tool: it mounts ChatPanel so the chatbot surface can be chatted with in
// one place. The AI-enable/disable toggle that used to live here now has its production
// home on the admin Projects card (admin2/ProjectsPage.tsx) — to chat-test, enable
// "Chatbot" for your own project on /admin/projects first, then open this page.
// Delete this file (and its /dev-chat route in App.tsx) once Batch B mounts ChatPanel
// for real (floating icon / assessment / lesson mounts).
import ChatPanel from '../components/ChatPanel'

export default function DevChat() {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 24, padding: 24, background: '#fafafa', fontFamily: 'var(--dlw-font-body)' }}>
      <div style={{ height: '70vh', width: 480, border: '1px solid #E2E2E2', borderRadius: 12, background: '#fff' }}>
        <ChatPanel kind="chatbot" />
      </div>
    </div>
  )
}
