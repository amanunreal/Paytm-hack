// WhatsApp is simulated (PLAN.md), so this shows what the agent wrote and says so.
export default function PhoneMockup({ events, owner }) {
  const messages = events.filter((event) => event.kind === 'whatsapp')
  if (messages.length === 0) return null

  return (
    <section className="phone-wrap" aria-label={`Simulated WhatsApp messages to ${owner}`}>
      <div className="phone">
        <div className="phone-header">
          <strong>Wapsi</strong>
          <span>WhatsApp to {owner}</span>
        </div>
        <div className="phone-chat">
          {messages.map((message) => (
            <div className="bubble" key={message.id}>
              <span lang={message.detail?.language}>{message.detail?.text}</span>
              <time dateTime={message.ts}>{message.ts.slice(11, 16)}</time>
            </div>
          ))}
        </div>
      </div>
      <p className="muted">Simulated: no WhatsApp message is sent.</p>
    </section>
  )
}
