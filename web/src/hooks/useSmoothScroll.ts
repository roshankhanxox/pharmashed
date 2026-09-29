/**
 * Lenis smooth scrolling for an inner scroll container.
 *
 * The app scrolls inside panes (overflow-y-auto divs), not the window, so Lenis is
 * attached to each pane via a callback ref. It is created when the pane mounts and
 * destroyed when it unmounts. Lenis disables itself when the user prefers reduced motion.
 */
import { useCallback, useRef } from "react";
import Lenis from "lenis";

/** Returns a callback ref; put it on the scrollable element. */
export function useSmoothScroll(): (node: HTMLElement | null) => void {
  const lenisRef = useRef<Lenis | null>(null);

  return useCallback((node: HTMLElement | null) => {
    lenisRef.current?.destroy();
    lenisRef.current = null;
    if (node) {
      lenisRef.current = new Lenis({ wrapper: node, content: node, autoRaf: true, lerp: 0.1 });
    }
  }, []);
}
