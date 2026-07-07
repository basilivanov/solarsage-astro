// ############################################################################
// AI_HEADER: MODULE_TODAY_PAGE
// ROLE: Legacy /today compatibility route for the migrated real-data day page.
// DEPENDENCIES: next/navigation
// GRACE_ANCHORS: [TODAY_REDIRECT]
// ############################################################################

import { redirect } from "next/navigation"

export default function TodayPage() {
  redirect("/day/today")
}
