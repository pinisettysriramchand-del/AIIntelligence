# Stage 4H Verification — UI L1/L2/L3 + minimal charts

**Status:** COMPLETE  
**Date:** 2026-08-09

## Scope
Part 4 § UI hierarchy: Executive Signal (L1), Explanation (L2), Action (L3), plus minimal charts (trend line, ranked bars, health meter).

## Files changed
- `apps/web/app/dashboard/page.tsx` — L1/L2/L3 layout
- `apps/web/app/decisions/[id]/page.tsx` — layered detail + forecast sparkline
- `apps/web/components/charts/{SparkLine,BarChart,HealthMeter}.tsx`
- `apps/web/lib/charts.ts`
- `apps/web/app/globals.css` — layer/chart styles + mobile nav
- `tests/unit/test_ui_l1_l2_l3.py`
- docs updates

## Features
| Level | Content |
|-------|---------|
| **L1** | Business health meter, primary KPI, major risk & opportunity |
| **L2** | Trend sparkline (prior/now/forecast), domain composition bars, driver bars, KPI comparisons, timeline, DQ strip |
| **L3** | Decision cards with recommendation, expected outcome, next-step link |

Charts are lightweight SVG/CSS (no new npm chart dependency).

## Limitations
- Charts need numeric prior/forecast values; otherwise explanatory copy is shown
- No interactive chart brushing/filters yet
- Desktop-first; mobile keeps summaries via responsive CSS

## Manual check
1. Login → Dashboard shows L1 / L2 / L3 section labels  
2. With KPIs that have prior values, primary trend line renders  
3. Open a decision card with forecast → dashed forecast segment on sparkline  
