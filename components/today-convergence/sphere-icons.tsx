// ############################################################################
// AI_HEADER: MODULE_TODAY_CONVERGENCE_SPHERE_ICONS — canonical outline icons for product spheres.
// ROLE: Render the twelve neutral 24px SVG metaphors used by the sphere navigator.
// ############################################################################

// START_MODULE_CONTRACT: M-SPHERE-ICONS
// purpose: Provide one consistent stroke-only icon for every canonical product sphere.
// owns:
//   - components/today-convergence/sphere-icons.tsx
// inputs: canonical ProductSphereKey and optional SVG presentation props.
// outputs: currentColor SVG icon with a stable 24px viewBox.
// dependencies: react types; lib/display/sphere-labels.
// side_effects: none.
// emitted_logs: none.
// invariants: every sphere has an icon; icons use stroke 1.5, no fill, and currentColor.
// failure_policy: TypeScript prevents unsupported sphere keys at call sites.
// END_MODULE_CONTRACT: M-SPHERE-ICONS

// START_MODULE_MAP: M-SPHERE-ICONS
// public_entrypoints:
//   - SphereIcon
//   - SphereIconKey
// semantic_blocks:
//   - ICON_SPRITES: twelve canonical geometric outline icons.
// owned_tests:
//   - __tests__/components/today-convergence/today-screen.test.tsx
// END_MODULE_MAP: M-SPHERE-ICONS

import type { ReactNode, SVGProps } from "react";
import type { ProductSphereKey } from "@/lib/display/sphere-labels";

export type SphereIconKey = ProductSphereKey;

type IconProps = SVGProps<SVGSVGElement>;

function IconFrame({ children, ...props }: IconProps & { children: ReactNode }) {
  return (
    <svg
      {...props}
      aria-hidden={props["aria-label"] ? undefined : true}
      focusable="false"
      viewBox="0 0 24 24"
      width="24"
      height="24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {children}
    </svg>
  );
}

// START_BLOCK: ICON_SPRITES
export function SphereIcon({ sphere, ...props }: IconProps & { sphere: SphereIconKey }) {
  // START_FUNCTION_CONTRACT: F-M-SPHERE-ICONS.SphereIcon
  // purpose: Render the canonical neutral outline metaphor for one product sphere.
  // inputs: sphere — canonical product sphere key; props — optional SVG attributes.
  // returns: 24px SVG icon in currentColor with a consistent stroke treatment.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: all supported keys render a deterministic icon.
  // END_FUNCTION_CONTRACT: F-M-SPHERE-ICONS.SphereIcon
  const icon = (() => {
    switch (sphere) {
      case "work":
        return (
          <>
            <rect x="3" y="7" width="18" height="13" rx="2" />
            <path d="M8 7V5h8v2M3 12h18" />
            <path d="M10 12v2h4v-2" />
          </>
        );
      case "finance":
        return (
          <>
            <circle cx="12" cy="12" r="8" />
            <path d="M12 8v8M15 10c-.5-.7-1.2-1-2.2-1h-1.1c-1.1 0-2 .7-2 1.6s.8 1.4 2 1.6l1 .2c1.2.2 2 .8 2 1.7s-.9 1.6-2 1.6h-1.1c-1 0-1.7-.3-2.2-1" />
          </>
        );
      case "documents":
        return (
          <>
            <path d="M6 3.5h8l4 4V20.5H6z" />
            <path d="M14 3.5v4h4M9 12h6M9 15.5h6" />
          </>
        );
      case "relationships":
        return (
          <>
            <circle cx="8" cy="12" r="4.5" />
            <circle cx="16" cy="12" r="4.5" />
            <path d="M11.5 9.5h1M11.5 14.5h1" />
          </>
        );
      case "sport":
        return <path d="M3 13h3l2-5 4 10 2-6 2 3h5" />;
      case "communication":
        return (
          <>
            <path d="M4 5.5h16v10H9l-4 3v-3H4z" />
            <path d="M8 9.5h8M8 12.5h5" />
          </>
        );
      case "health":
        return (
          <>
            <path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.5A4 4 0 0 1 19 10c0 5.6-7 10-7 10Z" />
            <path d="M12 10v5M9.5 12.5h5" />
          </>
        );
      case "home_family":
        return (
          <>
            <path d="M4 11 12 4l8 7" />
            <path d="M6.5 9.5V20h11V9.5" />
            <path d="M10 20v-5h4v5" />
          </>
        );
      case "travel":
        return <path d="M4 18 20 6M12 6h8v8M4 18h8v-8" />;
      case "creativity":
        return <path d="m12 3 1.5 6.5L20 12l-6.5 1.5L12 20l-1.5-6.5L4 12l6.5-2.5zM19 3v3M17.5 4.5h3" />;
      case "study":
        return (
          <>
            <path d="M4 5.5c2.5-1 5.5-.3 8 1.5v12c-2.5-1.8-5.5-2.5-8-1.5z" />
            <path d="M20 5.5c-2.5-1-5.5-.3-8 1.5v12c2.5-1.8 5.5-2.5 8-1.5z" />
          </>
        );
      case "friends_goals":
        return (
          <>
            <circle cx="12" cy="12" r="8" />
            <circle cx="12" cy="12" r="4.5" />
            <circle cx="12" cy="12" r="1" />
          </>
        );
    }
  })();

  return <IconFrame data-testid={`sphere-icon-${sphere}`} {...props}>{icon}</IconFrame>;
}
// END_BLOCK: ICON_SPRITES
