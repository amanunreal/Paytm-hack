import { useState } from 'react'
import { shortDay } from './labels'

// Two charts, not one with two axes: payments and heartbeats have different scales.
function Bars({ title, signals, field, hovered, onHover }) {
  const peak = Math.max(...signals.map((day) => day[field]), 1)
  return (
    <figure className="chart">
      <figcaption>
        <span>{title}</span>
        <span className="muted">peak {peak}</span>
      </figcaption>
      <div className="bars" role="img" aria-label={`${title}, last ${signals.length} days. See the table view for values.`}>
        {signals.map((day) => (
          <div
            key={day.day}
            className={`bar-slot ${hovered === day.day ? 'bar-slot-active' : ''}`}
            onMouseEnter={() => onHover(day.day)}
          >
            <div className="bar" style={{ height: `${(day[field] / peak) * 100}%` }} />
          </div>
        ))}
      </div>
    </figure>
  )
}

export default function SignalCharts({ signals }) {
  const [hovered, setHovered] = useState(null)
  if (signals.length === 0) return null
  const day = signals.find((item) => item.day === hovered) ?? signals.at(-1)

  return (
    <section aria-labelledby="signals-title">
      <div className="section-head">
        <h2 id="signals-title">Last {signals.length} days</h2>
        <p className="muted readout">
          {shortDay(day.day)}: {day.txn_count} QR payments, Rs {day.gmv.toLocaleString('en-IN')},{' '}
          {day.heartbeats > 0 ? `${day.heartbeats} heartbeats` : 'no heartbeat'}
        </p>
      </div>
      <div onMouseLeave={() => setHovered(null)}>
        <Bars title="QR payments per day" signals={signals} field="txn_count" hovered={hovered} onHover={setHovered} />
        <Bars title="Box heartbeats per day" signals={signals} field="heartbeats" hovered={hovered} onHover={setHovered} />
      </div>
      <div className="axis muted">
        <span>{shortDay(signals[0].day)}</span>
        <span>{shortDay(signals.at(-1).day)}</span>
      </div>
      <details>
        <summary>Table view</summary>
        <table className="compact">
          <thead>
            <tr>
              <th scope="col">Day</th>
              <th scope="col" className="number">QR payments</th>
              <th scope="col" className="number">Value (Rs)</th>
              <th scope="col" className="number">Heartbeats</th>
              <th scope="col" className="number">Signal</th>
            </tr>
          </thead>
          <tbody>
            {signals.map((item) => (
              <tr key={item.day}>
                <td>{shortDay(item.day)}</td>
                <td className="number">{item.txn_count}</td>
                <td className="number">{item.gmv.toLocaleString('en-IN')}</td>
                <td className="number">{item.heartbeats}</td>
                <td className="number">{item.signal ?? '–'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </section>
  )
}
