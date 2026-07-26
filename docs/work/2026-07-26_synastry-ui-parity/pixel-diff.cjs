// Computed-style diff: prototype (8899) vs impl (3000, fixtures)
const { chromium } = require('/opt/solarsage-astro/node_modules/.pnpm/playwright@1.60.0/node_modules/playwright')
const IMPL = 'http://127.0.0.1:3000/synastry'
const PID = '11111111-2222-3333-4444-555555555555'

const PROPS = ['font-family','font-size','font-weight','line-height','letter-spacing','color','background-color','border-radius','padding','text-transform','border-color','box-shadow']

// selector map: [name, protoSel, implSel]
const LIST_POINTS = [
  ['h1', 'h1', '[data-testid="synastry-list-hero"] h1'],
  ['lead', '.lead', '[data-testid="synastry-list-hero"] p:not(.mb-2)'],
  ['cta', '.primary.full', '[data-testid="synastry-add-btn"]'],
  ['search', '.search', '[data-testid="synastry-search-filters"] input'],
  ['filter-active', '.filter.active', '[data-testid="synastry-filter-all"]'],
  ['section-h2', '.section-head h2', '[data-testid="synastry-list"] h2, [data-testid="synastry-screen"] h2'],
  ['card', '.candidate', '[data-testid="synastry-card"]'],
  ['card-name', '.candidate-name', '[data-testid="synastry-card"] h3'],
  ['card-avatar', '.candidate .avatar', '[data-testid="synastry-card"] [class*="h-[46px]"]'],
  ['card-score', '.candidate .score', '[data-testid="synastry-card"] .text-right .syn-serif'],
  ['status-pill', '.candidate .cand-status, .status', '[data-testid="synastry-card"] [class*="rounded-full"]'],
  ['counter-tile', '.astro-mini span', '[data-testid="synastry-card-counters"] > div'],
]

async function grab(page, sel) {
  return page.evaluate(([sel, props]) => {
    const el = document.querySelector(sel)
    if (!el) return null
    const cs = getComputedStyle(el)
    const out = {}
    for (const p of props) out[p] = cs.getPropertyValue(p)
    const r = el.getBoundingClientRect()
    out['_w'] = Math.round(r.width); out['_h'] = Math.round(r.height)
    out['_text'] = (el.textContent||'').trim().slice(0,30)
    return out
  }, [sel, PROPS])
}

;(async () => {
  const browser = await chromium.launch()
  // PROTO
  const p1 = await (await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 })).newPage()
  await p1.goto('http://127.0.0.1:8899/', { waitUntil: 'networkidle' })
  await p1.waitForTimeout(600)
  // IMPL with fixtures
  const partners = [{ id: PID, name: 'Максим', relationType: 'romantic', birthDate: '1987-09-09', precision: 'exact', score: 89, status: 'good', reportState: 'ready', counters: { good: 8, mid: 2, bad: 2 }, summary: 'Много естественной поддержки: легко разговаривать, сближаться и действовать вместе. Главное напряжение — темп и контроль.', createdAt: '2026-07-20T12:00:00Z' }]
  const p2 = await (await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 })).newPage()
  await p2.route('**/api/**', route => {
    const p = new URL(route.request().url()).pathname
    const json = b => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(b) })
    if (p === '/api/synastry') return json({ partners })
    if (p === '/api/synastry/capabilities') return json({ canCalculate: true })
    return json({})
  })
  await p2.goto(IMPL, { waitUntil: 'domcontentloaded' })
  await p2.waitForSelector('[data-testid="synastry-screen"][data-state="ready"]', { timeout: 45000 })
  await p2.waitForTimeout(600)

  console.log('POINT | PROP | PROTO | IMPL')
  for (const [name, ps, is] of LIST_POINTS) {
    const a = await grab(p1, ps)
    const b = await grab(p2, is)
    if (!a) { console.log(`${name} | PROTO-SELECTOR-MISS (${ps})`); continue }
    if (!b) { console.log(`${name} | IMPL-SELECTOR-MISS (${is})`); continue }
    for (const prop of PROPS) {
      if (a[prop] !== b[prop]) console.log(`${name} | ${prop} | ${a[prop]} | ${b[prop]}`)
    }
  }
  await browser.close()
})().catch(e => { console.error(e); process.exit(1) })
