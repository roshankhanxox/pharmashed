/**
 * Lenis smooth scrolling for an inner scroll container.
 *
 * The app scrolls inside panes (overflow-y-auto divs), not the window, so Lenis is
 * attached to each pane via a callback ref. It is created when the pane mounts and
 * destroyed when it unmounts. Lenis disables itself when the user prefers reduced motion.
 *
 * Lenis measures the scroll height once and only re-measures when its content element
 * changes size. Here the wrapper and content are the same fixed-size element, so content
 * that loads later (for example the FHIR bundle viewer) would leave a stale, too-short
 * scroll limit. A MutationObserver re-measures whenever the pane's children change.
 */
import { useCallback, useRef } from "react";
import Lenis from "lenis";

/** Returns a callback ref; put it on the scrollable element. */
export function useSmoothScroll(): (node: HTMLElement | null) => void {
  const disposeRef = useRef<(() => void) | null>(null);

  return useCallback((node: HTMLElement | null) => {
    disposeRef.current?.();
    disposeRef.current = null;
    if (!node) return;

    const lenis = new Lenis({ wrapper: node, content: node, autoRaf: true, lerp: 0.1 });

    let frame = 0;
    const remeasure = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => lenis.resize());
    };
    const observer = new MutationObserver(remeasure);
    observer.observe(node, { childList: true, subtree: true, characterData: true });
    window.addEventListener("resize", remeasure);

    disposeRef.current = () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      window.removeEventListener("resize", remeasure);
      lenis.destroy();
    };
  }, []);
}
