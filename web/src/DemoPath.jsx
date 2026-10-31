import { useEffect } from 'react'

// The stage path from PLAN.md, so nobody hunts through lists mid-demo. It only shows
// with ?demo in the URL, so the normal product view stays clean. Arrow keys work too.
const STEPS = [
  { href: '#/', label: 'Board' },
  { href: '#/cases/C-M0418', label: 'Live call' },
  { href: '#/cases/C-M0044', label: 'Device fault' },
  { href: '#/cases/C-M0285', label: 'Billing fix' },
  { href: '#/cases/C-M0235', label: 'Waiver blocked' },
  { href: '#/manager', label: 'Manager' },
  { href: '#/results', label: 'Results' },
]

export default function DemoPath({ hash }) {
  const current = STEPS.findIndex((step) => step.href === (hash || '#/'))

  useEffect(() => {
    const onKey = (event) => {
      const move = { ArrowRight: 1, ArrowLeft: -1 }[event.key]
      const next = STEPS[current + move]
      if (next) window.location.hash = next.href
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [current])

  return (
    <ol className="demo-path" aria-label="Demo path">
      {STEPS.map((step, index) => (
        <li key={step.href}>
          <a href={step.href} aria-current={index === current ? 'step' : undefined}>
            <span className="demo-step">{index + 1}</span>
            {step.label}
          </a>
        </li>
      ))}
    </ol>
  )
}
