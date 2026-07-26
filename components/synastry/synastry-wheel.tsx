// ############################################################################
// AI_HEADER: MODULE_SYNASTRY_WHEEL
// ROLE: Interactive two-ring SVG interaction wheel for synastry report screen
// DEPENDENCIES: react, framer-motion, lucide-react, lib/astro/chart-geometry, components/astro/astro-chart-tokens, lib/api/synastry
// ############################################################################

// START_MODULE_CONTRACT: M-SYNASTRY-WHEEL
// purpose: Render two-ring SVG chart with zodiac sectors, planet nodes, aspect lines, and interactive selection popover.
// owns:
//   - components/synastry/synastry-wheel.tsx
// inputs: ownerPlanets, partnerPlanets, aspects, precision, partnerName, selection, onPlanetSelect, onAspectSelect, onAspectOpen
// outputs: SynastryWheel TSX render
// dependencies: lib/astro/chart-geometry, components/astro/astro-chart-tokens, lib/api/synastry
// side_effects: none
// emitted_logs: none
// failure_policy: fallback placeholder if planet data is missing
// END_MODULE_CONTRACT: M-SYNASTRY-WHEEL

// START_MODULE_MAP: M-SYNASTRY-WHEEL
// public_entrypoints:
//   - SynastryWheel
// semantic_blocks: none
// owned_tests:
//   - __tests__/synastry/synastry-wheel.test.tsx
// END_MODULE_MAP: M-SYNASTRY-WHEEL

"use client"

import { useMemo } from "react"
import { AnimatePresence, motion } from "framer-motion"
import { Info, X } from "lucide-react"

import type { SynastryAspectItem, SynastryPlanetPoint } from "@/lib/api/synastry"
import {
  describeArc,
  longitudeToAngle,
  polarToCartesian,
  resolveCollisionOffsets,
} from "@/lib/astro/chart-geometry"
import {
  ASPECT_COLORS_BY_TONE,
  PLANET_COLORS,
  PLANET_MEANINGS,
  PLANET_RU_NAMES,
  PLANET_SYMBOLS,
  SIGN_RU_NAMES,
  SIGN_RU_NAMES_PREPOSITIONAL,
  SIGN_SYMBOLS,
} from "@/components/astro/astro-chart-tokens"

export interface SynastryWheelSelection {
  selectedPlanetId: string | null
  selectedAspectId: string | null
}

type Props = {
  ownerPlanets?: SynastryPlanetPoint[]
  partnerPlanets?: SynastryPlanetPoint[]
  aspects?: SynastryAspectItem[]
  precision?: "exact" | "approximate"
  partnerName: string
  selection: SynastryWheelSelection
  onPlanetSelect: (planetId: string | null) => void
  onAspectSelect: (aspectId: string | null) => void
  onAspectOpen: (aspectId: string) => void
}

const ZODIAC_SIGNS = [
  "Aries",
  "Taurus",
  "Gemini",
  "Cancer",
  "Leo",
  "Virgo",
  "Libra",
  "Scorpio",
  "Sagittarius",
  "Capricorn",
  "Aquarius",
  "Pisces",
]

// START_BLOCK: SYNASTRY_WHEEL
export function SynastryWheel({
  ownerPlanets = [],
  partnerPlanets = [],
  aspects = [],
  precision = "exact",
  partnerName,
  selection,
  onPlanetSelect,
  onAspectSelect,
  onAspectOpen,
}: Props) {
  const isApproximate = precision === "approximate"
  const hasPlanets = ownerPlanets.length > 0 && partnerPlanets.length > 0

  const { selectedPlanetId, selectedAspectId } = selection

  // Geometry dimensions
  const size = 340
  const center = 170
  const zodiacOuterR = 162
  const zodiacInnerR = 144
  const partnerRingR = 126
  const ownerRingR = 92

  // 1. Calculate resolved planet node angles & Cartesian positions
  const ownerNodes = useMemo(() => {
    if (!ownerPlanets.length) return []
    const rawLons = ownerPlanets.map((p) => p.longitude)
    const resolvedLons = resolveCollisionOffsets(rawLons, 8.0)
    return ownerPlanets.map((p, idx) => {
      const angle = longitudeToAngle(resolvedLons[idx])
      const pos = polarToCartesian(center, center, ownerRingR, angle)
      return { ...p, angle, x: pos.x, y: pos.y }
    })
  }, [ownerPlanets, ownerRingR, center])

  const partnerNodes = useMemo(() => {
    if (!partnerPlanets.length) return []
    const rawLons = partnerPlanets.map((p) => p.longitude)
    const resolvedLons = resolveCollisionOffsets(rawLons, 8.0)
    return partnerPlanets.map((p, idx) => {
      const angle = longitudeToAngle(resolvedLons[idx])
      const pos = polarToCartesian(center, center, partnerRingR, angle)
      return { ...p, angle, x: pos.x, y: pos.y }
    })
  }, [partnerPlanets, partnerRingR, center])

  // Lookup dictionary for quick point access by ID
  const allNodesMap = useMemo(() => {
    const map = new Map<string, (typeof ownerNodes)[0]>()
    for (const node of ownerNodes) map.set(node.id, node)
    for (const node of partnerNodes) map.set(node.id, node)
    return map
  }, [ownerNodes, partnerNodes])

  // Selected planet node details
  const selectedNode = selectedPlanetId ? allNodesMap.get(selectedPlanetId) : null

  // Connected aspect IDs for currently selected planet
  const connectedAspectIds = useMemo(() => {
    if (!selectedPlanetId) return new Set<string>()
    const set = new Set<string>()
    for (const asp of aspects) {
      if (asp.ownerPlanetKey === selectedPlanetId || asp.partnerPlanetKey === selectedPlanetId) {
        set.add(asp.id)
      }
    }
    return set
  }, [selectedPlanetId, aspects])

  if (!hasPlanets) {
    return (
      <div className="space-y-4" data-testid="synastry-wheel-canvas">
        <div className="rounded-[20px] border border-border/50 bg-card p-6 text-center space-y-2">
          <p className="text-[13px] text-muted-foreground">
            Интерактивная карта связей будет доступна после завершения расчёта.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4" data-testid="synastry-wheel-canvas">
      <div className="relative w-full max-w-[360px] mx-auto rounded-[24px] bg-gradient-to-b from-[#f1e9f4]/50 to-transparent dark:from-[#2d2233]/40 p-3">
        <svg
          viewBox={`0 0 ${size} ${size}`}
          className="w-full h-auto chart-svg-root select-none overflow-visible"
          role="img"
          aria-label={`Карта взаимодействия с ${partnerName}`}
        >
          <defs>
            <radialGradient id="synastry-disk-glow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#795a86" stopOpacity="0.12" />
              <stop offset="100%" stopColor="#795a86" stopOpacity="0.0" />
            </radialGradient>
          </defs>

          {/* Background disk glow */}
          <circle cx={center} cy={center} r={zodiacOuterR} fill="url(#synastry-disk-glow)" />

          {/* Zodiac Outer Ring (12 Sectors) */}
          {ZODIAC_SIGNS.map((sign, idx) => {
            const startAngle = idx * 30
            const endAngle = (idx + 1) * 30
            const midAngle = startAngle + 15
            const arcPath = describeArc(center, center, zodiacOuterR, startAngle, endAngle)
            const isEven = idx % 2 === 0
            const iconPos = polarToCartesian(center, center, (zodiacOuterR + zodiacInnerR) / 2, midAngle)

            return (
              <g key={sign}>
                <path
                  d={`${arcPath} L ${center} ${center} Z`}
                  fill={isEven ? "rgba(121, 90, 134, 0.04)" : "rgba(121, 90, 134, 0.01)"}
                  stroke="rgba(121, 90, 134, 0.12)"
                  strokeWidth="1"
                />
                <text
                  x={iconPos.x}
                  y={iconPos.y}
                  textAnchor="middle"
                  dominantBaseline="central"
                  className="fill-foreground/45 text-[11px] font-sans font-medium"
                >
                  {SIGN_SYMBOLS[sign] || sign.slice(0, 2)}
                </text>
              </g>
            )
          })}

          {/* Concentric Guide Circles */}
          <circle cx={center} cy={center} r={zodiacInnerR} fill="none" stroke="rgba(121, 90, 134, 0.2)" strokeWidth="1" />
          <circle cx={center} cy={center} r={partnerRingR} fill="none" stroke="rgba(121, 90, 134, 0.15)" strokeWidth="1" strokeDasharray="3 3" />
          <circle cx={center} cy={center} r={ownerRingR} fill="none" stroke="rgba(121, 90, 134, 0.2)" strokeWidth="1" />

          {/* Center Glow & Title */}
          <circle cx={center} cy={center} r={55} fill="var(--card)" stroke="rgba(121, 90, 134, 0.25)" strokeWidth="1.5" />
          <text
            x={center}
            y={center - 4}
            textAnchor="middle"
            dominantBaseline="central"
            className="fill-muted-foreground text-[9.5px] font-medium uppercase tracking-[0.14em]"
          >
            СВЯЗЬ
          </text>
          <text
            x={center}
            y={center + 10}
            textAnchor="middle"
            dominantBaseline="central"
            className="fill-foreground font-serif font-semibold text-[13.5px]"
          >
            ТЫ + {partnerName}
          </text>

          {/* Aspect Lines */}
          {aspects.map((asp) => {
            const ownerPlanetName = (asp as any).ownerPlanet || (asp.ownerPlanetKey ? asp.ownerPlanetKey.replace("owner_", "") : "")
            const partnerPlanetName = (asp as any).partnerPlanet || (asp.partnerPlanetKey ? asp.partnerPlanetKey.replace("partner_", "") : "")

            const ownerNode = allNodesMap.get(asp.ownerPlanetKey || `owner_${ownerPlanetName.toLowerCase()}`)
            const partnerNode = allNodesMap.get(asp.partnerPlanetKey || `partner_${partnerPlanetName.toLowerCase()}`)

            if (!ownerNode || !partnerNode) return null

            const isSelected = selectedAspectId === asp.id
            const isConnectedToSelectedPlanet = selectedPlanetId && connectedAspectIds.has(asp.id)
            const isDimmed =
              (selectedAspectId && !isSelected) ||
              (selectedPlanetId && !isConnectedToSelectedPlanet)

            const strokeColor = ASPECT_COLORS_BY_TONE[asp.tone] || "#b07b36"
            const strokeWidth = isSelected ? 3.5 : isConnectedToSelectedPlanet ? 2.5 : 1.8
            const opacity = isSelected ? 1.0 : isConnectedToSelectedPlanet ? 0.9 : isDimmed ? 0.08 : 0.55

            const opNameRu = PLANET_RU_NAMES[ownerPlanetName] || ownerPlanetName
            const ppNameRu = PLANET_RU_NAMES[partnerPlanetName] || partnerPlanetName
            const aspectAriaLabel = `Твой ${opNameRu} — ${asp.title} — ${ppNameRu} партнёра`

            const handleLineClick = () => {
              onAspectSelect(asp.id)
              onAspectOpen(asp.id)
            }

            return (
              <g
                key={asp.id}
                role="button"
                tabIndex={0}
                aria-label={aspectAriaLabel}
                onClick={handleLineClick}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault()
                    handleLineClick()
                  }
                }}
                className="cursor-pointer focus:outline-none"
              >
                {/* Wide transparent hit line */}
                <line
                  x1={ownerNode.x}
                  y1={ownerNode.y}
                  x2={partnerNode.x}
                  y2={partnerNode.y}
                  stroke="transparent"
                  strokeWidth="14"
                />
                {/* Visible aspect line */}
                <line
                  x1={ownerNode.x}
                  y1={ownerNode.y}
                  x2={partnerNode.x}
                  y2={partnerNode.y}
                  stroke={strokeColor}
                  strokeWidth={strokeWidth}
                  strokeOpacity={opacity}
                  strokeLinecap="round"
                  className="transition-all duration-200"
                />
              </g>
            )
          })}

          {/* Owner Planet Nodes (Inner Ring) */}
          {ownerNodes.map((node) => {
            const isSelected = selectedPlanetId === node.id
            const isAspectSelectedNode =
              selectedAspectId &&
              aspects.some(
                (a) => a.id === selectedAspectId && (a.ownerPlanetKey === node.id || a.partnerPlanetKey === node.id)
              )
            const color = PLANET_COLORS[node.planet] || "#795a86"
            const glyph = PLANET_SYMBOLS[node.planet] || node.planet.slice(0, 2)
            const pRu = PLANET_RU_NAMES[node.planet] || node.planet
            const sRuPrep = SIGN_RU_NAMES_PREPOSITIONAL[node.sign || ""] || node.sign || ""

            const ariaLabel = `Твоё ${pRu}${sRuPrep ? ` в ${sRuPrep}` : ""}`

            return (
              <g
                key={node.id}
                role="button"
                tabIndex={0}
                aria-label={ariaLabel}
                onClick={() => onPlanetSelect(isSelected ? null : node.id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault()
                    onPlanetSelect(isSelected ? null : node.id)
                  }
                }}
                className="cursor-pointer focus:outline-none"
              >
                {/* Transparent hit area */}
                <circle cx={node.x} cy={node.y} r={15} fill="transparent" />
                {/* Node disk */}
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={isSelected || isAspectSelectedNode ? 12 : 9.5}
                  fill="var(--card)"
                  stroke={color}
                  strokeWidth={isSelected || isAspectSelectedNode ? 2.5 : 1.5}
                  className="transition-all duration-200 shadow-sm"
                />
                {/* Glyph text */}
                <text
                  x={node.x}
                  y={node.y}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fill={color}
                  className="text-[11px] font-sans font-bold"
                >
                  {glyph}
                </text>
              </g>
            )
          })}

          {/* Partner Planet Nodes (Outer Ring) */}
          {partnerNodes.map((node) => {
            const isSelected = selectedPlanetId === node.id
            const isAspectSelectedNode =
              selectedAspectId &&
              aspects.some(
                (a) => a.id === selectedAspectId && (a.ownerPlanetKey === node.id || a.partnerPlanetKey === node.id)
              )
            const color = PLANET_COLORS[node.planet] || "#3e3347"
            const glyph = PLANET_SYMBOLS[node.planet] || node.planet.slice(0, 2)
            const pRu = PLANET_RU_NAMES[node.planet] || node.planet
            const sRuPrep = SIGN_RU_NAMES_PREPOSITIONAL[node.sign || ""] || node.sign || ""
            const houseStr = node.houseReliable && node.house ? `, ${node.house} дом` : ""

            const ariaLabel = `${pRu} партнёра${sRuPrep ? ` в ${sRuPrep}` : ""}${houseStr}`

            return (
              <g
                key={node.id}
                role="button"
                tabIndex={0}
                aria-label={ariaLabel}
                onClick={() => onPlanetSelect(isSelected ? null : node.id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault()
                    onPlanetSelect(isSelected ? null : node.id)
                  }
                }}
                className="cursor-pointer focus:outline-none"
              >
                {/* Transparent hit area */}
                <circle cx={node.x} cy={node.y} r={15} fill="transparent" />
                {/* Node disk */}
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={isSelected || isAspectSelectedNode ? 12 : 9.5}
                  fill="var(--card)"
                  stroke={color}
                  strokeWidth={isSelected || isAspectSelectedNode ? 2.5 : 1.5}
                  className="transition-all duration-200 shadow-sm"
                />
                {/* Glyph text */}
                <text
                  x={node.x}
                  y={node.y}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fill={color}
                  className="text-[11px] font-sans font-bold"
                >
                  {glyph}
                </text>
              </g>
            )
          })}
        </svg>

        {/* Legend */}
        <div className="flex items-center justify-center gap-4 text-[11px] text-muted-foreground pt-2">
          <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-[#43806d]" /> поддержка</span>
          <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-[#b07b36]" /> неоднозначно</span>
          <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-[#a64d59]" /> напряжение</span>
        </div>
      </div>

      {/* Animated Selected Planet Popover */}
      <AnimatePresence>
        {selectedNode && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            transition={{ duration: 0.18 }}
            data-testid="synastry-planet-popover"
            className="rounded-[20px] border border-border/70 bg-card p-4 shadow-md space-y-2 relative"
          >
            <button
              type="button"
              aria-label="Закрыть информацию планете"
              onClick={() => onPlanetSelect(null)}
              className="absolute top-3 right-3 text-muted-foreground hover:text-foreground p-1"
            >
              <X className="h-4 w-4" />
            </button>

            <div className="flex items-center gap-2.5">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-primary font-bold text-[16px]">
                {PLANET_SYMBOLS[selectedNode.planet] || selectedNode.planet.slice(0, 2)}
              </span>
              <div>
                <h4 className="font-serif text-[16px] font-semibold text-foreground leading-snug">
                  {selectedNode.owner === "user" ? "Твоё" : "Партнёра"}{" "}
                  {PLANET_RU_NAMES[selectedNode.planet] || selectedNode.planet}
                </h4>
                <div className="text-[12px] text-muted-foreground">
                  Знак: {SIGN_RU_NAMES[selectedNode.sign || ""] || selectedNode.sign || "—"}
                  {selectedNode.houseReliable && selectedNode.house
                    ? ` · ${selectedNode.house} дом`
                    : ""}
                </div>
              </div>
            </div>

            <p className="text-[13px] leading-relaxed text-foreground/80 pt-1">
              {(PLANET_MEANINGS && PLANET_MEANINGS[selectedNode.planet]) || "Функция планеты в натальной карте."}
            </p>

            {isApproximate && selectedNode.owner === "partner" && !selectedNode.houseReliable && (
              <div className="flex items-center gap-1 text-[11px] text-amber-800 dark:text-amber-200 italic pt-1">
                <Info className="h-3 w-3 flex-none" />
                <span>Дом партнёра не рассчитан (время неизвестно)</span>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
// END_BLOCK: SYNASTRY_WHEEL
