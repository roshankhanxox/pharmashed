/** Typeset a LaTeX formula with KaTeX. Loaded lazily (see index.tsx) so the maths library stays out of the main bundle.
 * The input is always one of our own fixed strings, never user text. */
import katex from "katex";
import "katex/dist/katex.min.css";

export default function Tex({ tex, block = false }: { tex: string; block?: boolean }) {
  const html = katex.renderToString(tex, { displayMode: block, throwOnError: false, output: "html" });
  return <span dangerouslySetInnerHTML={{ __html: html }} />;
}
