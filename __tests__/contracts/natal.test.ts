import { describe, it, expect } from 'vitest'
import {
  validateNatalReport,
  NatalReportSchema,
  HighlightSchema,
  SphereScoreSchema,
  PlanetScoreSchema,
} from '../../lib/contracts/natal'

function validMinimalReport() {
  return {
    schemaVersion: 'natal/v1' as const,
    meta: {
      name: 'Test User',
      birth: { date: '1990-06-15' },
    },
    sections: [
      {
        id: 's1',
        title: 'Overview',
        blocks: [{ type: 'paragraph' as const, text: 'Hello world' }],
      },
    ],
  }
}

function validFullReport() {
  return {
    schemaVersion: 'natal/v1' as const,
    meta: {
      name: 'Test User',
      birth: {
        date: '1990-06-15',
        time: '14:30',
        timezone: 'Europe/Moscow',
        place: 'Moscow',
      },
      mode: 'classic',
      houseSystem: 'Placidus',
      generatedAt: '2026-06-01T12:00:00Z',
    },
    highlights: [
      { id: 'h1', label: 'Sun', value: 'Leo', hint: 'The core self' },
    ],
    spheres: [
      { id: 'sp1', title: 'Career', dominance: 3 },
    ],
    planets: [
      { id: 'p1', name: 'Sun', sign: 'Leo', house: 1 },
    ],
    sections: [
      {
        id: 's1',
        title: 'Full Section',
        eyebrow: 'Part I',
        summary: 'A summary of this section',
        blocks: [
          { type: 'lead', text: 'Lead text here' },
          { type: 'heading', level: 2 as const, text: 'Chapter One' },
          { type: 'paragraph', text: 'Paragraph content' },
          { type: 'list', style: 'bullet' as const, items: ['item 1', 'item 2'] },
          { type: 'callout', tone: 'strength' as const, title: 'Note', text: 'Important note' },
          {
            type: 'pros_cons',
            prosLabel: 'Strengths',
            consLabel: 'Weaknesses',
            pros: ['pro1'],
            cons: ['con1'],
          },
          {
            type: 'stat_grid',
            items: [
              { label: 'Stat A', value: '10' },
              { label: 'Stat B', value: '20' },
            ],
          },
          { type: 'quote', text: 'A great quote', cite: 'Author' },
          { type: 'divider' },
          { type: 'spheres_widget', limit: 3 },
          { type: 'planets_widget' },
        ],
      },
    ],
  }
}

describe('validateNatalReport', () => {
  it('validates a minimal valid report', () => {
    expect(() => validateNatalReport(validMinimalReport())).not.toThrow()
  })

  it('validates a full valid report with all optional fields', () => {
    expect(() => validateNatalReport(validFullReport())).not.toThrow()
  })

  it('rejects report with wrong schemaVersion', () => {
    const data = { ...validMinimalReport(), schemaVersion: 'natal/v2' }
    expect(() => validateNatalReport(data)).toThrow()
  })

  it('rejects report with missing schemaVersion', () => {
    const { schemaVersion, ...data } = validMinimalReport()
    expect(() => validateNatalReport(data)).toThrow()
  })

  it('rejects report with missing meta', () => {
    const { meta, ...data } = validMinimalReport()
    expect(() => validateNatalReport(data)).toThrow()
  })

  it('rejects report with missing sections', () => {
    const { sections, ...data } = validMinimalReport()
    expect(() => validateNatalReport(data)).toThrow()
  })

  it('accepts report with empty sections array (no min length on array)', () => {
    const data = { ...validMinimalReport(), sections: [] }
    expect(() => validateNatalReport(data)).not.toThrow()
  })

  it('rejects report with empty meta name', () => {
    const data = validMinimalReport()
    data.meta.name = ''
    expect(() => validateNatalReport(data)).toThrow()
  })

  it('rejects report with invalid birth date format', () => {
    const data = validMinimalReport()
    data.meta.birth.date = '15-06-1990'
    expect(() => validateNatalReport(data)).toThrow()
  })

  it('rejects section with empty id', () => {
    const data = validMinimalReport()
    data.sections[0].id = ''
    expect(() => validateNatalReport(data)).toThrow()
  })

  it('rejects section with empty title', () => {
    const data = validMinimalReport()
    data.sections[0].title = ''
    expect(() => validateNatalReport(data)).toThrow()
  })

  it('rejects block with invalid type', () => {
    const data = validMinimalReport()
    data.sections[0].blocks = [{ type: 'unknown', text: '???' }]
    expect(() => validateNatalReport(data)).toThrow()
  })

  it('rejects paragraph block with empty text', () => {
    const data = validMinimalReport()
    data.sections[0].blocks = [{ type: 'paragraph', text: '' }]
    expect(() => validateNatalReport(data)).toThrow()
  })

  it('rejects heading block with invalid level', () => {
    const data = validMinimalReport()
    data.sections[0].blocks = [{ type: 'heading', level: 4, text: 'Too deep' }]
    expect(() => validateNatalReport(data)).toThrow()
  })

  it('rejects list block with empty items array', () => {
    const data = validMinimalReport()
    data.sections[0].blocks = [{ type: 'list', items: [] }]
    expect(() => validateNatalReport(data)).toThrow()
  })

  it('rejects pros_cons block with wrong type content', () => {
    const data = validMinimalReport()
    data.sections[0].blocks = [{ type: 'pros_cons', pros: 'not_an_array' }]
    expect(() => validateNatalReport(data)).toThrow()
  })
})

describe('HighlightSchema', () => {
  it('validates a correct highlight', () => {
    const h = { id: 'h1', label: 'Sun', value: 'Leo', hint: 'Core' }
    expect(() => HighlightSchema.parse(h)).not.toThrow()
  })

  it('rejects highlight with empty id', () => {
    expect(() => HighlightSchema.parse({ id: '', label: 'x', value: 'y' })).toThrow()
  })
})

describe('SphereScoreSchema', () => {
  it('validates a correct sphere score', () => {
    const s = { id: 's1', title: 'Career', dominance: 3 }
    expect(() => SphereScoreSchema.parse(s)).not.toThrow()
  })

  it('rejects dominance > 5', () => {
    const s = { id: 's1', title: 'Career', dominance: 6 }
    expect(() => SphereScoreSchema.parse(s)).toThrow()
  })
})

describe('PlanetScoreSchema', () => {
  it('validates a correct planet score', () => {
    const p = { id: 'p1', name: 'Sun', sign: 'Leo' }
    expect(() => PlanetScoreSchema.parse(p)).not.toThrow()
  })

  it('rejects planet with empty sign', () => {
    expect(() => PlanetScoreSchema.parse({ id: 'p1', name: 'Sun', sign: '' })).toThrow()
  })
})
