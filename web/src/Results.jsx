import * as api from './api'
import { CAUSES, percent } from './labels'
import { usePoll } from './usePoll'

const rupees = (amount) => `Rs ${amount.toLocaleString('en-IN')}`
const signed = (amount) => `+${amount}`

const MEASURES = [
  { key: 'visits', title: 'Field visits', format: String },
  { key: 'cost', title: 'Cost', format: rupees },
  { key: 'won_back', title: 'Merchants won back', format: String },
]

// One chart per measure: they have different units, so they cannot share an axis.
function Compare({ title, ai, control, format }) {
  const peak = Math.max(ai, control, 1)
  const rows = [
    { label: 'With Wapsi', value: ai, series: 'series-ai' },
    { label: 'Control', value: control, series: 'series-control' },
  ]
  return (
    <figure className="compare">
      <figcaption>{title}</figcaption>
      {rows.map((row) => (
        <div className="compare-row" key={row.label} title={`${row.label}: ${format(row.value)}`}>
          <span className="muted">{row.label}</span>
          <div className="compare-track">
            <div className={`compare-bar ${row.series}`} style={{ width: `${(row.value / peak) * 100}%` }} />
          </div>
          <span className="compare-value">{format(row.value)}</span>
        </div>
      ))}
    </figure>
  )
}

export default function Results() {
  const { data: results, error } = usePoll(api.getResults)
  const back = <a className="back" href="#/">← Board</a>

  if (!results) {
    return (
      <>
        {back}
        {error
          ? <p className="alert" role="alert">Cannot reach the API on port 8000.</p>
          : <p className="muted">Loading results…</p>}
      </>
    )
  }

  const { ai, control, assumptions } = results
  const tiles = [
    ['Field visits saved', control.visits - ai.visits],
    ['Cost saved', rupees(control.cost - ai.cost)],
    ['Extra merchants won back', signed(results.incremental_won_back)],
    [`Rent kept over ${assumptions.months_kept} months`, rupees(results.rent_kept)],
  ]

  return (
    <>
      {back}
      <header className="topbar">
        <div className="brand">
          <h1>Results</h1>
          <p className="muted">AI group vs control, {ai.merchants} merchants in each</p>
        </div>
        <span className="badge badge-stub">Simulated</span>
      </header>

      {error && <p className="alert" role="alert">Cannot refresh. Showing the last results we received.</p>}

      <p className="banner banner-simulated">
        <strong>These outcomes are simulated</strong> from the assumptions on this page. They are not
        measured on real merchants or Paytm data.
      </p>

      <main className="results">
        <section className="tiles" aria-label="Headline results">
          {tiles.map(([label, value]) => (
            <div className="tile" key={label}>
              <div className="tile-value">{value}</div>
              <div className="muted">{label}</div>
            </div>
          ))}
        </section>

        <section className="panel" aria-labelledby="compare-title">
          <div className="panel-title">
            <h2 id="compare-title">AI group vs control</h2>
            <div className="legend muted">
              <span><i className="legend-mark series-ai" /> With Wapsi</span>
              <span><i className="legend-mark series-control" /> Control</span>
            </div>
          </div>
          <div className="compare-grid">
            {MEASURES.map(({ key, title, format }) => (
              <Compare key={key} title={title} ai={ai[key]} control={control[key]} format={format} />
            ))}
          </div>
          <details>
            <summary>Table view</summary>
            <table className="compact">
              <thead>
                <tr>
                  <th scope="col">Measure</th>
                  <th scope="col" className="number">With Wapsi</th>
                  <th scope="col" className="number">Control</th>
                </tr>
              </thead>
              <tbody>
                {MEASURES.map(({ key, title, format }) => (
                  <tr key={key}>
                    <td>{title}</td>
                    <td className="number">{format(ai[key])}</td>
                    <td className="number">{format(control[key])}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
        </section>

        <section className="panel" aria-labelledby="assumptions-title">
          <h2 id="assumptions-title">Assumptions</h2>
          <div className="assumptions">
            <table className="compact">
              <caption className="muted">Chance a merchant is back at 70% of normal after 7 days</caption>
              <thead>
                <tr>
                  <th scope="col">Cause</th>
                  <th scope="col" className="number">With Wapsi</th>
                  <th scope="col" className="number">Control</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(assumptions.recovery_with_wapsi_vs_control).map(([cause, [withWapsi, without]]) => (
                  <tr key={cause}>
                    <td>{CAUSES[cause] ?? cause}</td>
                    <td className="number">{percent(withWapsi)}</td>
                    <td className="number">{percent(without)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <dl className="facts">
              <dt>Field visit</dt>
              <dd>{rupees(assumptions.visit_cost)} each. Every control case costs one visit.</dd>
              <dt>Wapsi contact</dt>
              <dd>{rupees(assumptions.call_cost)} per AI case</dd>
              <dt>Device rent</dt>
              <dd>{rupees(assumptions.avg_rent)} a month on average, kept for {assumptions.months_kept} months</dd>
              <dt>Left out</dt>
              <dd>Closed or seasonal shops, which Wapsi does not chase</dd>
              <dt>As of</dt>
              <dd>{results.as_of}. Field visits update as the manager decides.</dd>
            </dl>
          </div>
        </section>
      </main>
    </>
  )
}
