// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_HORARY_TEST
// ROLE: Generated contract tests for horary question and answer payloads
// DEPENDENCIES: generated OpenAPI and TypeScript contracts
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Verify generated horary question and answer contract shapes
// owns:
//   - __tests__/contracts/horary.test.ts
// inputs: Generated OpenAPI schemas and TypeScript contract types
// outputs: Assertion results
// dependencies: packages/contracts
// side_effects: n/a (tests)
// emitted_logs: n/a (tests)
// invariants:
//   - Horary block discriminators resolve to horary-specific schemas
//   - Horary question failure fields remain represented in generated contracts
// failure_policy: log and raise
// END_MODULE_CONTRACT
import { describe, expect, it } from 'vitest'
import openapi from '../../packages/contracts/openapi.json'
import type {
  HoraryAnswerRead,
  HoraryQuestionRead,
} from '../../packages/contracts/horary'
import { HoraryQuestionSchema } from '../../lib/contracts/horary'

const answer = {
  verdict: 'yes',
  confidence: 0.82,
  confidenceLabel: 'high',
  confidenceExplanation: 'The main testimonies agree.',
  blocks: [
    { type: 'paragraph', text: 'The chart supports the matter.' },
    { type: 'lead', text: 'The answer is favorable.' },
    { type: 'heading', level: 2, text: 'Key testimonies' },
    { type: 'list', style: 'check', items: ['Moon applies to the ruler.'] },
    {
      type: 'callout',
      tone: 'insight',
      title: 'Context',
      text: 'Timing depends on the applying aspect.',
    },
    {
      type: 'pros_cons',
      prosLabel: 'Support',
      consLabel: 'Risks',
      pros: ['Strong reception'],
      cons: ['Slow timing'],
    },
    { type: 'divider' },
    { type: 'quote', text: 'The significators perfect.', source: 'Chart' },
  ],
  planets: ['Moon', 'Saturn'],
  generatedAt: '2026-07-05T20:00:00Z',
} satisfies HoraryAnswerRead

const failedQuestion = {
  id: 'horary-question-1',
  text: 'Will the contract be signed?',
  category: 'career',
  status: 'failed',
  spentCreditSource: 'paid',
  creditRefunded: true,
  clientTimezone: 'Europe/Moscow',
  clientLocalTime: null,
  questionLocationName: 'Moscow',
  failureStage: 'interpretation',
  publicErrorCode: 'HORARY_INTERPRETATION_FAILED',
  publicErrorMessage: 'The interpretation could not be completed.',
  createdAt: '2026-07-05T19:59:00Z',
  answer: null,
  chart: null,
} satisfies HoraryQuestionRead

const chartQuestion = {
  id: 'horary-question-2',
  text: 'Will the contract be signed?',
  category: 'career',
  status: 'answered',
  spentCreditSource: 'paid',
  creditRefunded: false,
  clientTimezone: 'Europe/Moscow',
  clientLocalTime: '2026-07-05T19:59:00',
  questionLocationName: 'Moscow',
  createdAt: '2026-07-05T19:59:00Z',
  answer,
  chart: {
    source: 'solarsage',
    castAt: '2026-07-05T19:59:00',
    timezone: 'Europe/Moscow',
    latitude: 55.75,
    longitude: 37.62,
    locationName: 'Moscow',
    houseSystem: 'PLACIDUS',
    houses: [{ number: 1, cusp: 11.2, sign: 'Aries' }],
    planets: [{ name: 'Moon', longitude: 60.5, sign: 'Gemini', latitude: 0, speed: 13.1 }],
    aspects: [{ planet: 'Moon', targetPlanet: 'Saturn', aspectType: 'trine', orb: 1.2 }],
  },
} satisfies HoraryQuestionRead

describe('generated horary contracts', () => {
  it('maps answer block discriminators to horary-specific schemas', () => {
    const blockItems =
      openapi.components.schemas.HoraryAnswerRead.properties.blocks.items

    expect(blockItems.discriminator.mapping).toMatchObject({
      paragraph: '#/components/schemas/app__schemas__horary__ParagraphBlock',
      lead: '#/components/schemas/app__schemas__horary__LeadBlock',
      heading: '#/components/schemas/app__schemas__horary__HeadingBlock',
      list: '#/components/schemas/app__schemas__horary__ListBlock',
      callout: '#/components/schemas/app__schemas__horary__CalloutBlock',
      pros_cons: '#/components/schemas/app__schemas__horary__ProsConsBlock',
      divider: '#/components/schemas/app__schemas__horary__DividerBlock',
      quote: '#/components/schemas/app__schemas__horary__QuoteBlock',
    })
    expect(answer.blocks.map((block) => block.type)).toEqual([
      'paragraph',
      'lead',
      'heading',
      'list',
      'callout',
      'pros_cons',
      'divider',
      'quote',
    ])
  })

  it('keeps question failure details and nullable answers in the contract', () => {
    const questionSchema = openapi.components.schemas.HoraryQuestionRead

    expect(questionSchema.properties).toHaveProperty('failureStage')
    expect(questionSchema.properties).toHaveProperty('publicErrorCode')
    expect(questionSchema.properties).toHaveProperty('publicErrorMessage')
    expect(questionSchema.properties).toHaveProperty('chart')
    expect(failedQuestion).toMatchObject({
      status: 'failed',
      creditRefunded: true,
      failureStage: 'interpretation',
      publicErrorCode: 'HORARY_INTERPRETATION_FAILED',
      answer: null,
      chart: null,
    })
    expect(HoraryQuestionSchema.parse(failedQuestion).chart).toBeNull()
  })

  it('keeps persisted horary chart snapshots in generated and local contracts', () => {
    const chartSchema = openapi.components.schemas.HoraryChartSnapshot

    expect(chartSchema.properties).toMatchObject({
      source: expect.any(Object),
      castAt: expect.any(Object),
      timezone: expect.any(Object),
      houses: expect.any(Object),
      planets: expect.any(Object),
      aspects: expect.any(Object),
    })
    expect(chartQuestion.chart).toMatchObject({
      source: 'solarsage',
      latitude: 55.75,
      planets: [{ name: 'Moon', longitude: 60.5, sign: 'Gemini' }],
      aspects: [{ planet: 'Moon', targetPlanet: 'Saturn', aspectType: 'trine', orb: 1.2 }],
    })
    expect(HoraryQuestionSchema.parse(chartQuestion).chart).toEqual(chartQuestion.chart)
  })

  it('requires chart on question payloads while allowing null for legacy rows', () => {
    const { chart: _chart, ...missingChart } = failedQuestion

    expect(HoraryQuestionSchema.safeParse(missingChart).success).toBe(false)
    expect(HoraryQuestionSchema.safeParse({ ...failedQuestion, chart: null }).success).toBe(true)
  })
})
