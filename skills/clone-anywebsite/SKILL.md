---
name: clone-anywebsite
description: >-
  Clone any website's landing page with pixel-perfect fidelity. Visual-first
  workflow: screenshot → sniper CSS extraction → deep DOM interrogation →
  animation detection → rebuild in React + Tailwind + Framer Motion. Uses AdaL
  browser-use agent tools. Includes ready-to-use extraction scripts, gotcha
  catalog, quality checklist, and speedrun prompt.
author: SylphAI-Inc
version: 2.0.0
---

# Guide: Visual-First Web Cloning Recipe v2

When building a high-fidelity landing page clone, the biggest trap is relying purely on DOM trees and CSS dumps. Modern website builders (Framer, Webflow) generate deeply nested "div soup" and obfuscated CSS to create visual effects.

**The Golden Rule:** Trust your "eyes" (screenshots) first, but when an effect looks too complex to be pure CSS, use **Deep DOM Interrogation** to steal the exact asset — never guess the math.

> **Tool note:** This guide uses AdaL browser-use agent tools (`navigate`, `javascript_tool`, `computer`, `resize_window`, `tabs_context`, `bash`). If you're not on AdaL, the same JS payloads work with Chrome DevTools MCP (`evaluate_script`), Playwright (`page.evaluate`), or any browser automation tool — just swap the invocation wrapper.

## The 80/20 Cloning Philosophy

Divide your workflow into two phases so you don't get bogged down pixel-pushing too early:

1. **The 80% Sprint (Speed & Structure):** Get the page laid out rapidly. Fetch the semantic HTML, scaffold the React component tree (`Navbar`, `Hero`, `Features`), and apply basic Tailwind for layout (Flex/Grid) and spacing. Accept approximations — solid colors instead of gradients, standard shadows, static backgrounds. **Move fast.**
2. **The 20% Polish (Pixel Perfection & Physics):** Once the structure is on screen, shift to meticulous engineering. Use "Sniper CSS" to extract exact multi-stop gradients, rip WebGL canvas backgrounds to `.webm`, map massive multi-layer box-shadows, and implement Framer Motion spring physics.

---

## The 4-Phase Workflow

### Phase 1: Visual Discovery

**Goal:** Understand what you're cloning before touching code.

#### Step 0: Screenshot Matrix (3 Viewports)

Always capture the target at multiple sizes before coding. Do not optimize only for the first screenshot.

| Viewport | Purpose | Required? |
|---|---|---|
| `1440×1400` | Primary desktop comparison target | Always |
| `1920×1200` or larger | Detects false fixed-left layouts and max-width issues | Always |
| `390×844` or `430×932` | Mobile hero layout and nav behavior | Always unless user says desktop-only |

```
navigate("https://target-site.com/")
tabs_context                                   // confirm tab_id
resize_window(tab_id=1, width=1440, height=1400)
javascript_tool(tab_id=1, action="javascript_exec", text="window.scrollTo(0, 0); 'ok';")
computer(tab_id=1, action="wait", duration=2)  // let animations settle
computer(tab_id=1, action="screenshot")        // desktop hero

resize_window(tab_id=1, width=1920, height=1200)
computer(tab_id=1, action="wait", duration=2)
computer(tab_id=1, action="screenshot")        // large desktop

resize_window(tab_id=1, width=390, height=1400)
computer(tab_id=1, action="wait", duration=2)
computer(tab_id=1, action="screenshot")        // mobile
```

#### Step 1: The "Eye Test" (Visual Grounding)

**Before looking at a single line of code, visually ground yourself in the reference site.**

Read your screenshots and actively identify the *Vibe*:
- **Backgrounds:** Is it flat? A subtle radial gradient? Sweeping SVG waves? Floating blurred orbs? Star/particle field?
- **Buttons:** Are they flat? Glassmorphic (backdrop-blur)? Glowing auras? Multi-layer shadows?
- **Typography:** Which specific words are highlighted? Gradient text clips? Tight negative letter-spacing?
- **Badges/pills:** Compound components (pill-in-a-pill)?

#### Step 2: Macro Structure Capture (Semantic HTML)

Pull a text/structure snapshot — grab the section landmarks and real copy in one shot:

```
javascript_tool(tab_id=1, action="javascript_exec", text="
(() => JSON.stringify({
  h1: document.querySelector('h1')?.innerText,
  navLinks: Array.from(document.querySelectorAll('nav a')).map(a => a.innerText.trim()).filter(Boolean),
  buttons: Array.from(document.querySelectorAll('a, button')).map(b => b.innerText.trim()).filter(Boolean).slice(0, 12),
  sections: Array.from(document.querySelectorAll('section')).length
}, null, 2))()
")
```

**Do NOT blindly copy the DOM.** Distill the complicated nested builder divs into clean, semantic React (`<nav>`, `<section>`, `<h1>`, `<button>`). A 12-deep Framer `<div>` chain becomes one `<button>`. Note: Framer often duplicates button text (`"Book a callBook a call"`) — dedupe it.

#### Step 3: Micro Extraction (Sniper CSS)

Extract exact pixel-perfect design tokens. **Never dump the full `getComputedStyle` object** — it returns 500+ properties, overwhelms your context window, and creates hallucination. Use the targeted scripts in the **Sniper CSS Script Library** below.

#### Step 4: Animation Detection

Landing page animations come from many sources. Don't assume canvas = animation. Run this comprehensive scanner to detect what's powering the motion:

```
javascript_tool(tab_id=1, action="javascript_exec", text="
(() => {
  const results = { animations: [], tech: {}, elements: {} };

  // A. CSS Animations & Transitions
  const allEls = document.querySelectorAll('*');
  const cssAnimated = [];
  allEls.forEach(el => {
    const s = getComputedStyle(el);
    if (s.animationName && s.animationName !== 'none') {
      cssAnimated.push({ tag: el.tagName, class: el.className?.toString().slice(0, 60), animation: s.animationName, duration: s.animationDuration });
    }
  });
  results.animations.push({ type: 'css', count: cssAnimated.length, samples: cssAnimated.slice(0, 5) });

  // B. Canvas elements
  results.elements.canvas = Array.from(document.querySelectorAll('canvas')).map(c => ({
    width: c.width, height: c.height,
    ariaLabel: c.getAttribute('aria-label'),
    parentDataAttrs: Object.fromEntries([...(c.closest('[data-us-project],[data-scene-id]')?.attributes || [])].filter(a => a.name.startsWith('data-')).map(a => [a.name, a.value]))
  }));

  // C. Video elements
  results.elements.video = Array.from(document.querySelectorAll('video')).map(v => ({ src: v.src || v.querySelector('source')?.src || 'none', autoplay: v.autoplay, loop: v.loop, muted: v.muted }));

  // D. SVG animations
  results.elements.svgAnimations = document.querySelectorAll('svg animate, svg animateTransform, svg animateMotion').length;

  // E. Lottie / Rive / Spline
  results.elements.lottie = document.querySelectorAll('lottie-player, dotlottie-player, [class*="lottie"]').length;
  results.elements.rive = document.querySelectorAll('canvas[class*="rive"], [data-rive-src]').length;
  results.elements.spline = document.querySelectorAll('canvas[data-engine="spline"]').length;

  // F. iframes
  results.elements.iframes = Array.from(document.querySelectorAll('iframe')).map(f => ({ src: f.src?.slice(0, 150) }));

  // G. JS animation library globals
  results.tech.gsap = typeof window.gsap !== 'undefined';
  results.tech.threeJS = typeof window.THREE !== 'undefined';
  results.tech.lottie = typeof window.lottie !== 'undefined';
  results.tech.rive = typeof window.rive !== 'undefined';
  results.tech.anime = typeof window.anime !== 'undefined';
  results.tech.unicornStudio = typeof window.UnicornStudio !== 'undefined';
  results.tech.pixiJS = typeof window.PIXI !== 'undefined';
  results.tech.p5 = typeof window.p5 !== 'undefined';

  // H. Animation library scripts
  const scriptUrls = performance.getEntriesByType('resource').filter(r => r.name.match(/\.(js|mjs)$/i)).map(r => r.name).filter(s => !s.includes('google') && !s.includes('analytics') && !s.includes('gtm'));
  const sigs = ['gsap','three','lottie','rive','anime','framer-motion','popmotion','unicorn','spline','pixi','p5','mo.js','velocity','scroll-trigger','locomotive'];
  results.tech.animationScripts = scriptUrls.filter(url => sigs.some(sig => url.toLowerCase().includes(sig)));

  // I. Framer appear animations
  const framerAppear = document.querySelectorAll('[data-framer-appear-id]');
  results.tech.framerAppearElements = framerAppear.length;
  if (framerAppear.length > 0) {
    results.tech.framerAppearSample = Array.from(framerAppear).slice(0, 3).map(el => ({ id: el.getAttribute('data-framer-appear-id'), style: { opacity: el.style.opacity, transform: el.style.transform } }));
  }

  return JSON.stringify(results, null, 2);
})()
")
```

**Decision tree — interpret results:**

| What you found | Animation Tech | How to replicate |
|---|---|---|
| `unicornStudio: true` + canvas with `data-us-project` | **Unicorn Studio** (WebGL) | Embed: load their runtime JS + init with same project ID |
| `threeJS: true` + canvas | **Three.js** (3D WebGL) | Capture as looping video, or re-implement if simple |
| `lottie: true` or `elements.lottie > 0` | **Lottie** (After Effects → JSON) | Find the `.json` file, use `lottie-react` |
| `gsap: true` | **GSAP** (scroll/timeline) | Re-implement with GSAP or translate to Framer Motion |
| `elements.rive > 0` | **Rive** (interactive vector) | Find `.riv` file, use `@rive-app/react-canvas` |
| `elements.spline > 0` | **Spline** (3D web scenes) | Embed via iframe or `@splinetool/react-spline` |
| `elements.video` with autoplay+loop | **Pre-rendered video** background | Download the MP4/WebM and embed |
| `elements.svgAnimations > 0` | **SVG SMIL animation** | Copy the SVG markup including `<animate>` elements |
| `framerAppearElements > 0` + CSS transitions | **Framer entrance animations** | Extract delays/durations, rebuild with Framer Motion |
| CSS animations only, no libraries | **Pure CSS** | Extract `@keyframes` and `animation` properties |
| Nothing detected but things move | **Scroll-driven CSS** or **IntersectionObserver** | Check for `scroll-timeline`, `animation-timeline`, or custom JS observers |

#### Step 4b: GIF Recording & Analysis (Understand Effects)

The scanner tells you *what* tech powers the animation, but not *what it looks like in motion*. Animations are invisible to static CSS extraction. Use the browser-use agent's `gif_creator` tool to capture entrance animations, hover effects, and continuous motion as animated GIFs, then analyze the frames.

**How `gif_creator` works:** It records screenshots automatically on every `computer` action (click, scroll, screenshot, wait) and `navigate` call while recording is active. Max 50 frames per recording. Export produces an animated GIF with optional overlays (click indicators, action labels, progress bar, watermark). Use `download: true` to save to disk, or `coordinate: [x, y]` to drag-drop onto a page.

**Record the entrance animation:**
```
// 1. Start recording — clears any previous frames
gif_creator(tab_id=1, action="start_recording")

// 2. Navigate to trigger entrance animations (this captures the first frame)
navigate(tab_id=1, url="https://target-site.com/")

// 3. Capture frames at intervals to record the animation progression
//    Each screenshot call captures a frame automatically
computer(tab_id=1, action="wait", duration=0.3)
computer(tab_id=1, action="screenshot")   // frame: early entrance
computer(tab_id=1, action="wait", duration=0.5)
computer(tab_id=1, action="screenshot")   // frame: mid-animation
computer(tab_id=1, action="wait", duration=0.5)
computer(tab_id=1, action="screenshot")   // frame: near-settled
computer(tab_id=1, action="wait", duration=1.0)
computer(tab_id=1, action="screenshot")   // frame: settled
computer(tab_id=1, action="wait", duration=1.5)
computer(tab_id=1, action="screenshot")   // frame: final resting state

// 4. Stop recording (keeps frames for export)
gif_creator(tab_id=1, action="stop_recording")

// 5. Export as GIF — download to disk for analysis
gif_creator(
  tab_id=1,
  action="export",
  download=true,
  filename="entrance-animation.gif",
  options={showClickIndicators: false, showActionLabels: false, showProgressBar: true, quality: 5}
)
```

**Analyze the GIF** — the exported GIF is saved to the browser screenshot directory (default: `/tmp/adal_browser/`). Read it with your image tool and identify:
- Which elements appear/disappear across frames
- Animation type per element (fade, slide-up, scale, blur-to-sharp)
- Approximate timing and stagger order (frame timestamps are embedded)
- Continuous vs one-shot animations (does the glow keep rotating after everything settles?)

**Record hover/interaction effects:**
```
// 1. Start recording
gif_creator(tab_id=1, action="start_recording")

// 2. Capture resting state
computer(tab_id=1, action="screenshot")

// 3. Hover over the button to trigger the hover animation
computer(tab_id=1, action="hover", coordinate=[500, 400])
computer(tab_id=1, action="wait", duration=0.5)
computer(tab_id=1, action="screenshot")   // frame: hover state

// 4. Move away to capture the transition back
computer(tab_id=1, action="hover", coordinate=[10, 10])
computer(tab_id=1, action="wait", duration=0.3)
computer(tab_id=1, action="screenshot")   // frame: resting state restored

// 5. Stop and export
gif_creator(tab_id=1, action="stop_recording")
gif_creator(
  tab_id=1,
  action="export",
  download=true,
  filename="hover-effect.gif",
  options={showClickIndicators: true, showActionLabels: true, quality: 5}
)
```

**Record scroll-triggered animations:**
```
gif_creator(tab_id=1, action="start_recording")
computer(tab_id=1, action="screenshot")                          // frame: top of page
computer(tab_id=1, action="scroll", coordinate=[720, 400], scroll_direction="down", scroll_amount=3)
computer(tab_id=1, action="wait", duration=1.0)
computer(tab_id=1, action="screenshot")                          // frame: mid-scroll reveal
computer(tab_id=1, action="scroll", coordinate=[720, 400], scroll_direction="down", scroll_amount=3)
computer(tab_id=1, action="wait", duration=1.0)
computer(tab_id=1, action="screenshot")                          // frame: further down
gif_creator(tab_id=1, action="stop_recording")
gif_creator(tab_id=1, action="export", download=true, filename="scroll-animations.gif", options={quality: 5})
```

**Common Framer hero animation patterns** (discovered from real clone sessions):

| Element | Animation | Timing | Framer Motion |
|---------|-----------|--------|---------------|
| Glow/orb | Appears first, continuous morph/rotation | 0s (always visible) | CSS `@keyframes` or `animate={{ rotate: 360 }}` with `repeat: Infinity` |
| Navbar | Slide down + fade in | ~0.1-0.3s | `initial={{ y: -20, opacity: 0 }} animate={{ y: 0, opacity: 1 }}` |
| Badge ("New") | Fade + scale in | ~0.3-0.5s | `initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}` |
| H1 heading | Fade in + slide up | ~0.4-0.6s | `initial={{ y: 30, opacity: 0 }} animate={{ y: 0, opacity: 1 }}` |
| Description | Fade in + slide up | ~0.5-0.7s | Same pattern, staggered |
| CTA buttons | Fade in + slide up | ~0.6-0.8s | Same pattern, staggered |
| Stars/particles | Fade in | ~0.2-0.5s | `initial={{ opacity: 0 }} animate={{ opacity: 0.5 }}` |

**Key insight:** Most Framer hero animations use a simple **staggered fade-up** pattern. The glow/orb is the only continuously animated element. The GIF recording confirms the exact stagger order and timing.

**GIF tips:**
- Max 50 frames per recording — plan your capture sequence to stay under the limit
- Use `quality: 5` for higher-quality GIFs during analysis (lower number = better quality)
- Disable overlays (`showClickIndicators: false`, `showActionLabels: false`) for clean visual analysis
- Enable overlays (`showClickIndicators: true`) when recording for documentation or sharing
- Use `gif_creator(tab_id=1, action="clear")` to discard frames if you need to re-record

#### Step 5: Asset Extraction (SVGs, Logos, Videos)

- **Inline SVG:** Extract `outerHTML` via `javascript_tool`, then save with `bash`
- **Data-URI background logos:** Trust/logo carousels frequently render as CSS `background-image` data-URIs on `<div>`s — not `<img>` tags. Use Script 7 to find them, decode and save with `bash`
- **Background videos:** Capture as `.webm`/`.mp4` via canvas recorder (Script 10), store in `src/assets/media/`
- **Fonts:** Search `@font-face` rules and `performance.getEntriesByType('resource')` for `.woff2` URLs. Self-host in `assets/fonts/`

#### Step 6: Deep DOM Interrogation

When an effect (like a smooth background or a swirling button) is too complex, **do not guess the math**. Framer and Webflow hide these in layered divs, pseudo-elements, or literal `<video>`/`<canvas>` tags.

**Render Engine Identification** — find the full-screen background node to determine if it's a video, canvas, or CSS:

```
javascript_tool(tab_id=1, action="javascript_exec", text="
(() => {
  const backgrounds = [];
  document.querySelectorAll('*').forEach(el => {
    const style = window.getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    if ((style.position === 'fixed' || style.position === 'absolute') &&
        (parseInt(style.zIndex) <= 0 || style.zIndex === 'auto') &&
        rect.width >= window.innerWidth * 0.8 &&
        rect.height >= window.innerHeight * 0.5 &&
        el.tagName !== 'BODY' && el.tagName !== 'HTML') {
       backgrounds.push({ tag: el.tagName, html: el.outerHTML.substring(0, 300) });
    }
  });
  return JSON.stringify(backgrounds, null, 2);
})()
")
```

The DOM never lies. You might discover the "complex animation" is actually:
1. **A Video:** A `<video src="...mp4">` tag. *Solution: Extract the URL and drop it in.*
2. **A WebGL Canvas:** A `<canvas>` tag. *Solution: Record as video (Script 10) or re-implement with React Three Fiber.*
3. **A Noise Overlay:** A repeating film-grain image at 5-10% opacity layered over the effect to prevent color banding.

---

### Phase 2: Write the Clone Plan

Before writing a single line of code, create `docs/clone_plan.md`:

```markdown
# Clone Plan: [Site Name]

## Target
- URL: https://...
- Scope: Hero section only (or full page)
- Viewports: 1440×1400, 1920×1200+, mobile 390×844

## Tech Stack Discovery
- Framework: [Framer / Webflow / Custom]
- Animation: [Unicorn Studio / Three.js / Lottie / CSS / etc.]
- Fonts: [Font names + source URLs]

## Design Tokens
- Colors: [list with hex values]
- Typography: [h1, body, nav specs]
- Layout: [container width, heights, gaps]

## Assets to Extract
- [ ] Logo SVG
- [ ] Font files (self-host)
- [ ] Canvas/animation (embed or capture)
- [ ] Background images/videos

## Animation Strategy
- Hero entrance: [describe stagger sequence]
- Canvas/WebGL: [embed vs re-implement]
- Hover effects: [describe]

## Implementation Plan
1. Scaffold Vite + React + Tailwind
2. Build Navbar component
3. Build Hero component
4. Integrate animation
5. Polish + compare
```

---

### Phase 3: Build

1. **Scaffold** — `npm create vite@latest . -- --template react`, install Tailwind, set `base` for GitHub Pages
2. **Folder Structure:**
   ```
   src/
     components/
       layout/    # Navbar.tsx, Footer.tsx
       sections/  # Hero.tsx, Features.tsx
       ui/        # Button.tsx, Badge.tsx, GlassCard.tsx
     assets/
       media/     # extracted videos, noise overlays, icons, SVG logos
       fonts/     # self-hosted .woff2 files
     styles/
       globals.css  # font-face, CSS variables
   ```
3. **Build Components** — Navbar, Hero, with extracted design tokens. Map every value to Tailwind arbitrary values: `text-[70px]`, `tracking-[-2.2px]`, `max-w-[900px]`
4. **Integrate Animation** — Embed or re-implement based on Phase 1 findings
5. **Add Framer Motion** — Staggered entrance animations, hover effects, scroll triggers
6. **Center Layout** — Always use `max-w-[Xpx] mx-auto` for large-screen centering

**Framer Motion stagger pattern (covers 90% of hero animations):**
```jsx
import { motion } from 'framer-motion';

const container = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.12, delayChildren: 0.1 } }
};

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94] } }
};

<motion.div variants={container} initial="hidden" animate="visible">
  <motion.div variants={fadeUp}><Badge /></motion.div>
  <motion.div variants={fadeUp}><h1>...</h1></motion.div>
  <motion.div variants={fadeUp}><p>...</p></motion.div>
  <motion.div variants={fadeUp}><Buttons /></motion.div>
</motion.div>
```

---

### Phase 4: Compare & Polish

#### Side-by-Side Comparison

1. Open the original site and your clone in separate tabs:
   ```
   // Tab 1: Original
   navigate("https://target.framer.ai/")
   resize_window(tab_id=1, width=1440, height=1400)
   computer(tab_id=1, action="wait", duration=2)
   computer(tab_id=1, action="screenshot")

   // Tab 2: Your clone
   navigate("http://localhost:5173")  // opens new tab
   resize_window(tab_id=2, width=1440, height=1400)
   computer(tab_id=2, action="wait", duration=2)
   computer(tab_id=2, action="screenshot")
   ```

2. **Compare all required viewports** — desktop 1440×1400, large desktop 1920×1200+, and mobile 390×844

3. **Stitch for 1:1 comparison** — Use Python to stitch screenshots side-by-side:
   ```bash
   python3 -c "
   from PIL import Image
   i1 = Image.open('/absolute/path/ref.png')
   i2 = Image.open('/absolute/path/local.png')
   h = min(i1.height, i2.height)
   i1 = i1.resize((int(i1.width * h / i1.height), h))
   i2 = i2.resize((int(i2.width * h / i2.height), h))
   dst = Image.new('RGB', (i1.width + i2.width, h))
   dst.paste(i1, (0, 0))
   dst.paste(i2, (i1.width, 0))
   dst.save('/absolute/path/combined.png')
   "
   ```
   Read the stitched image to spot remaining visual discrepancies.

4. **The Build→Screenshot→Fix Loop:**
   - Screenshot clone + original → identify deltas with **pixel positions** ("Button is 116px wide, should be 90px", not "button is too wide")
   - Fix all deltas in one pass
   - Re-screenshot → repeat 2-3 rounds until matching

5. **Run the Quality Checklist** (below) before declaring done

---

## The 10 Gotchas

Real traps discovered cloning Framer/Webflow sites. Memorize these.

| # | Gotcha | Symptom | Solution |
|---|--------|---------|----------|
| 1 | **Framer nests text deeply** | `nav a` reports default browser styles: `rgb(0,0,238)`, `12px` | The real style is on a nested `<p>`/`<span>`. Walk the DOM tree with TreeWalker (Script 1F). |
| 2 | **Layered gradient orbs, not radial blur** | Background aura looks like a soft radial glow | It's **two overlapping gradient divs** with multi-stop *linear* gradients at specific angles, wrapped in a parent with `opacity` + `blur()`. Extract each orb separately (Script 5). |
| 3 | **Logos are data-URI backgrounds** | `document.querySelectorAll('img')` returns nothing for the trust carousel | Logos are inline `data:image/svg+xml` URIs set as CSS `background-image` on `<div>`s. Query `backgroundImage` (Script 7). |
| 4 | **Multi-layer box-shadows** | Your single shadow looks flat vs. the original's depth | Buttons can have **6 layers** of rgba shadows. Extract the full `boxShadow` string verbatim (Script 2). |
| 5 | **Compound badge ('New' pill)** | Badge looks like one element | It's an **outer pill** containing an **inner colored pill** + text. Build as nested components (Script 8). |
| 6 | **Star/particle backgrounds** | Faint texture behind hero you can't place | Full-width container at low opacity behind hero content. Rip as image/`.webm` or recreate with randomly-positioned absolute `<div>` dots. |
| 7 | **Negative letter-spacing everywhere** | Type looks "looser" than original | Framer sites use negative tracking site-wide (e.g., h1 `-2.2px`, body `-0.28px`). Extract and apply per element with `tracking-[-2.2px]`. |
| 8 | **Double text in Framer buttons** | DOM shows `"Book a callBook a call"` | Framer renders button text twice for a hover slide/swap animation. **Render it once**; optionally implement the hover text-swap with Framer Motion. |
| 9 | **getComputedStyle overload** | Context window flooded, hallucinated values | Snipe only needed properties. Never `JSON.stringify(getComputedStyle(el))`. |
| 10 | **Fluid wrapping ≠ original** | Headline wraps on a different word | Extract the container width and force it: `max-w-[900px]` (Script 4). |

### Browser-Use Agent Rules

| # | Rule |
|---|------|
| B1 | **Screenshots are viewport-only** — `resize_window` the height (e.g., 1400px) to fit a full section before screenshotting |
| B2 | **`javascript_tool` returns strings** — always wrap in an IIFE and `JSON.stringify()` your result. Returning a raw object gives `[object Object]` |
| B3 | **Framer deep nesting** — for any text style, use the TreeWalker pattern (Script 1F). Never trust the outer element's computed style |
| B4 | **Wait after scroll/resize** — always `computer(tab_id, action="wait", duration=2)` so animations/lazy content settle |
| B5 | **Always pass `tab_id`** — specify `tab_id` on every `computer` / `javascript_tool` / `resize_window` call |

---

## Sniper CSS Script Library

Copy-paste payloads for the AdaL browser-use agent. Each is an IIFE returning `JSON.stringify(...)`. Pass as the `text` argument to `javascript_tool(tab_id=1, action="javascript_exec", text="...")`.

### Script 1: Typography Tokens
```javascript
(() => {
  const el = document.querySelector('h1');
  const s = window.getComputedStyle(el);
  return JSON.stringify({ fontFamily: s.fontFamily, color: s.color, fontSize: s.fontSize, fontWeight: s.fontWeight, letterSpacing: s.letterSpacing, lineHeight: s.lineHeight }, null, 2);
})()
```

### Script 1F: Framer-Aware Typography (TreeWalker to Deepest Text Node)
*Why: `nav a` and many Framer headings report default browser styles. The real style is on a deeply nested `<p>`/`<span>`.*
```javascript
(() => {
  const root = document.querySelector('h1'); // change selector as needed
  if (!root) return "Not found";
  const target = (root.textContent || '').trim();
  let el = root;
  while (true) {
    const child = Array.from(el.children).find(c => (c.textContent || '').trim() === target);
    if (!child) break;
    el = child;
  }
  const s = window.getComputedStyle(el);
  return JSON.stringify({ matchedTag: el.tagName, fontFamily: s.fontFamily, color: s.color, fontSize: s.fontSize, fontWeight: s.fontWeight, letterSpacing: s.letterSpacing, lineHeight: s.lineHeight }, null, 2);
})()
```

### Script 2: Bounding Box, Overflow & Full Box-Shadow
```javascript
(() => {
  const btn = Array.from(document.querySelectorAll('a, button')).find(l => (l.textContent||'').includes('Get Started')) || document.querySelector('a, button');
  if (!btn) return "Not found";
  const r = btn.getBoundingClientRect();
  const s = window.getComputedStyle(btn);
  return JSON.stringify({ width: r.width, height: r.height, display: s.display, padding: s.padding, borderRadius: s.borderRadius, overflow: s.overflow, background: s.background, boxShadow: s.boxShadow }, null, 2);
})()
```

### Script 3: Glassmorphism & Backgrounds
```javascript
(() => {
  const el = document.querySelector('nav');
  const s = window.getComputedStyle(el);
  return JSON.stringify({ background: s.background, backdropFilter: s.backdropFilter || s.webkitBackdropFilter, border: s.border, borderRadius: s.borderRadius, height: el.getBoundingClientRect().height, padding: s.padding }, null, 2);
})()
```

### Script 4: Forced Line-Breaks (Container Width)
*Why: a clone looks fake if text wraps differently. Extract the exact width and lock it.*
```javascript
(() => {
  const el = document.querySelector('h1');
  const r = el.getBoundingClientRect();
  return JSON.stringify({ containerMaxWidth: r.width }, null, 2);
})()
```

### Script 5: Abstract Glows & Layered Orbs
*Why: auras are usually hard-shaped, multi-stop linear gradients with precise rotation + a tight blur — not a radial blob.*
```javascript
(() => {
  const hero = document.querySelector('section') || document.body;
  const orbs = Array.from(hero.querySelectorAll('div')).filter(d => {
    const s = getComputedStyle(d);
    return s.position === 'absolute' && s.backgroundImage.includes('gradient');
  }).slice(0, 6);
  return JSON.stringify(orbs.map(d => {
    const s = getComputedStyle(d); const r = d.getBoundingClientRect();
    return { size: Math.round(r.width)+'x'+Math.round(r.height), background: s.backgroundImage, transform: s.transform, filter: s.filter, opacity: s.opacity, mixBlendMode: s.mixBlendMode };
  }), null, 2);
})()
```

### Script 6: Named Framer Layer (by data-framer-name)
```javascript
(() => {
  const el = document.querySelector('[data-framer-name="Big Circle"]');
  if (!el) return "Not found";
  const s = window.getComputedStyle(el);
  return JSON.stringify({ background: s.backgroundImage, transform: s.transform, filter: s.filter, opacity: s.opacity }, null, 2);
})()
```

### Script 7: Data-URI Logo Extraction (Trust Carousels)
*Why: logos are CSS `background-image` data-URIs on `<div>`s, invisible to `img` queries.*
```javascript
(() => {
  const nodes = Array.from(document.querySelectorAll('div')).filter(d => getComputedStyle(d).backgroundImage.startsWith('url("data:image'));
  return JSON.stringify(nodes.slice(0, 20).map((d, i) => {
    const bg = getComputedStyle(d).backgroundImage;
    return { index: i, size: Math.round(d.getBoundingClientRect().width)+'x'+Math.round(d.getBoundingClientRect().height), uriPreview: bg.slice(0, 80) + '...', fullLength: bg.length };
  }), null, 2);
})()
```
> To save: read the full `backgroundImage`, strip `url("` / `")`, URL-decode the `data:image/svg+xml,...` payload, and write it to `src/assets/media/logo-N.svg` via `bash`.

### Script 8: Compound Component Audit (Badge / Pill-in-Pill)
```javascript
(() => {
  const inner = Array.from(document.querySelectorAll('div, span')).find(e => (e.textContent||'').trim() === 'New');
  if (!inner) return "Not found";
  const outer = inner.parentElement;
  const dump = el => { const s = getComputedStyle(el); return { background: s.background, borderRadius: s.borderRadius, padding: s.padding, color: s.color }; };
  return JSON.stringify({ outer: dump(outer), inner: dump(inner) }, null, 2);
})()
```

### Script 9: Pseudo-Element Extraction
```javascript
(() => {
  const el = document.querySelector('selector'); // change as needed
  if (!el) return "Not found";
  const s = window.getComputedStyle(el, '::before');
  return JSON.stringify({ content: s.content, background: s.background, width: s.width, height: s.height, transform: s.transform, filter: s.filter, opacity: s.opacity }, null, 2);
})()
```

### Script 10: Canvas Recorder (Last Resort for WebGL)
When a WebGL Canvas shader is too obfuscated to intercept, record the GPU output directly and use it as a looping background video:
```javascript
(() => {
  return new Promise((resolve) => {
    const canvas = document.querySelector('canvas');
    if (!canvas) return resolve("No canvas found.");
    const stream = canvas.captureStream(30);
    const recorder = new MediaRecorder(stream, { mimeType: 'video/webm' });
    const chunks = [];
    recorder.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data); };
    recorder.onstop = () => {
      const blob = new Blob(chunks, { type: 'video/webm' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'framer_perfect_loop.webm';
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      resolve("Recorded 8s and downloaded: framer_perfect_loop.webm");
    };
    recorder.start();
    setTimeout(() => recorder.stop(), 8000);
  });
})()
```

---

## Design Token Extraction Template

Document every extracted value in this format. Fill it in during discovery, reference it during build.

### Colors
| Token | Hex | RGB |
|-------|-----|-----|
| Page background | `#000000` | `rgb(0,0,0)` |
| Primary accent | `#814AC8` | `rgb(129,74,200)` |
| White text | `#FFFFFF` | `rgb(255,255,255)` |
| Description gray | `#CCCCCC` | `rgb(204,204,204)` |

### Typography
| Element | Size | Weight | Line-height | Letter-spacing | Notes |
|---------|------|--------|-------------|----------------|-------|
| H1 | 70px | 600 | 77px | -2.2px | max-width ~900px |
| Body / nav | 14px | 500 | 16.8px | -0.28px | |
| Description | 18px | 500 | 27px | -0.36px | |

**Font family:** `Figtree, "Figtree Placeholder", sans-serif` (load real Figtree; ignore the Placeholder shim).

### Spacing & Components
| Component | Value |
|-----------|-------|
| Navbar height | ~65px |
| Navbar padding | 10px 40px |
| Button border-radius | 6px |
| Button padding | 9px 13px |
| Badge outer | border-radius 20px, padding 2px 10px 2px 2px |
| Badge inner | border-radius 12px, padding 4px 8px |

### Tailwind Mapping (copy-paste pattern)
```jsx
<h1 className="text-[70px] font-semibold leading-[77px] tracking-[-2.2px] max-w-[900px] text-white">
<span className="text-[14px] font-medium leading-[16.8px] tracking-[-0.28px]">
<button className="rounded-[6px] px-[13px] py-[9px] bg-[#814AC8] text-white">
```

---

## Quality Checklist

Verify your clone before declaring done. Compare side-by-side with the reference at 1440px and 390px.

**Layout & Structure**
- [ ] Semantic HTML (`nav`, `section`, `h1`, `button`) — no copied div-soup
- [ ] Section order and spacing match
- [ ] Layout centers on large screens (`max-w-[Xpx] mx-auto`)
- [ ] Responsive breakpoints behave like the original

**Typography**
- [ ] Correct font family loaded (not a fallback)
- [ ] Font sizes, weights, line-heights match extracted tokens
- [ ] Negative letter-spacing applied per element
- [ ] Headline wraps on the same word (forced `max-w-[…]`)

**Color & Surfaces**
- [ ] Background color exact
- [ ] Translucent surfaces use the exact `rgba(...)`
- [ ] Text colors match

**Effects**
- [ ] Gradient orbs reproduced as separate layered divs (size, angle, blur, opacity)
- [ ] Multi-layer box-shadows copied verbatim
- [ ] Glassmorphism (`backdrop-filter`) present where used
- [ ] Star/particle/noise background layer present at correct opacity

**Components**
- [ ] Compound badge built as nested pills
- [ ] Buttons render text once (no Framer double-text)
- [ ] Hover micro-interactions implemented

**Assets**
- [ ] Trust/logo carousel extracted from data-URIs
- [ ] Inline SVGs saved as components
- [ ] WebGL/canvas backgrounds ripped to `.webm` and looping

**Animation**
- [ ] Entrance animation plays on load (stagger)
- [ ] Canvas/WebGL animation runs (if applicable)
- [ ] Hover effects work (buttons, nav links)

**Final**
- [ ] Side-by-side screenshot diff shows 90%+ fidelity at 1440×1400
- [ ] Large desktop (1920×1200+) confirms centered layout
- [ ] Mobile screenshot passes or is explicitly out of scope
- [ ] No console errors; fonts/assets load without flashes

---

## Speedrun Prompt

Copy-paste this to a browser-use agent to clone any hero section fast:

```
Clone the hero section of [TARGET_URL].

1. Navigate to the target. Resize to 1440x1400. Screenshot.
   Also capture 1920x1200 and 390x844 (mobile).

2. Extract ALL design tokens using javascript_tool:
   - Page background color
   - Navbar: bg, height, padding, link styles (use TreeWalker for real text styles)
   - H1: font-family, size, weight, line-height, letter-spacing, color, max-width
   - Description: same properties
   - Buttons: bg, color, padding, border-radius, box-shadow (capture ALL layers)
   - Badge/tags: structure, bg, border-radius, padding
   - Decorative elements: gradients, transforms, blur, opacity
   - Trust/logo bar: text styles + logo extraction (check data-URI backgrounds!)

3. Run the animation detection scanner. Identify the animation tech and strategy.

4. Extract assets:
   - Logo SVG: querySelector('svg').outerHTML → save to file
   - Trust logos: filter divs by backgroundImage data:image → decode → save
   - Fonts: find .woff2 URLs in @font-face or performance entries

5. Scaffold: npm create vite@latest . -- --template react && npm install tailwindcss
   Build ALL components in one pass using extracted tokens.
   Map every value to Tailwind arbitrary values.

6. Start dev server. Open clone in new tab. Screenshot both.
   Compare and fix with pixel-position-specific deltas. Repeat 2-3 times.
```

---

## Mandatory: Two-Agent Builder+Evaluator Pattern

**The builder MUST NOT evaluate its own output.** Always use **two separate browser-use workers** orchestrated by the AdaL Engineer supervisor. This is not optional — a single agent that both builds and judges its own clone produces measurably worse results.

### Recommended Models (Cost-Effective + Visual + Coding)

Cloning is token-intensive (screenshots, DOM extraction, many fix rounds). Use cost-effective models that support **vision** (for screenshot comparison) and **coding** (for React/Tailwind):

| Model | Input $/M | Output $/M | Vision | Why |
|-------|-----------|------------|--------|-----|
| **MiniMax M3** (recommended) | $0.30 | $1.20 | ✅ | Cheapest, strong coding, multimodal — best value for token-heavy clone sessions |
| Muse Spark 1.1 | $1.25 | $4.25 | ✅ | Good agentic coding, always-on reasoning — solid alternative |
| Grok 4.5 | $2.00 | $6.00 | ✅ | Strongest reasoning, but 4-5× the cost of MiniMax M3 |

**Default recommendation:** Use `minimax-MiniMax-M3` for both Builder and Evaluator workers. If you need stronger reasoning for a complex clone, use `grok-4.5` for the Evaluator only (it's the adversarial judge — reasoning quality matters most there).

```
# Builder — cost-effective, good at coding + vision
adal_worker_start(
  work_dir="/path/to/project",
  command=["adal", "--yolo", "--model", "minimax-MiniMax-M3", "--agent-mode", "browser-use"],
  launch_mode="attach", alias="builder"
)

# Evaluator — adversarial judge, can upgrade to grok-4.5 for harder cases
adal_worker_start(
  work_dir="/path/to/project",
  command=["adal", "--yolo", "--model", "minimax-MiniMax-M3", "--agent-mode", "browser-use"],
  launch_mode="attach", alias="evaluator"
)
```

### Worker 1 — Builder (Browser-Use)
One agent does the full visual loop: navigate target, screenshot matrix, extract CSS/fonts/assets, run animation scanner, scaffold and build the clone.

### Worker 2 — Evaluator (Browser-Use)
Separate session, adversarial prompt. After the builder finishes, the evaluator opens the live target and the clone in separate tabs, screenshots both at every viewport, compares pixel positions/colors/fonts/animation/content verbatim, and reports every failure with severity + file/line. Its system belief is "this clone is broken — prove it."

### Planning Contract (before any clone code)
1. **Builder** writes `team-log/builder_plan.md` (implementation approach, files, component breakdown, font/animation strategy)
2. **Evaluator** writes `team-log/test_plan.md` (visual fidelity matrix, animation verification, design-token assertions, responsive edge cases)
3. **Engineer** mediates — sends each plan to the other for critique, then writes `team-log/contract.md` with status `Approved to Build`
4. **Builder** codes only after the contract is accepted. Evaluator evaluates only after builder reports done.

### Build→Screenshot→Fix Loop
Each round:
1. Evaluator screenshots clone + original at matching viewports
2. Reports specific deltas with pixel positions: "H1 is 15px too high (clone y=579, original y=589)"
3. Builder applies all fixes in one pass
4. Repeat until the evaluator returns ACCEPT

---

## Deployment Checklist

- [ ] `vite.config.js` has `base: '/repo-name/'`
- [ ] `.github/workflows/deploy.yml` configured for GitHub Pages
- [ ] GitHub Pages enabled: `gh api repos/OWNER/REPO/pages -X POST -f build_type=workflow`
- [ ] `npm run build` passes
- [ ] Committed and pushed to main
- [ ] Workflow run succeeded

---

## Troubleshooting

- **"The background animation is missing!"** → You assumed it was CSS. Run the animation scanner (Step 4) to find the hidden `<video>`, `<canvas>`, or library.
- **"The Button looks totally different!"** → Extract the `outerHTML` of the button's parent. You likely missed overlapping blurred divs or 6-layer box shadows.
- **"The Text Wraps Wrong!"** → You let the browser decide fluidly. Extract the exact bounding box width (Script 4) and hardcode it (`max-w-[...]`).
- **"Nav link styles look wrong"** → Framer nests text deeply. Use the TreeWalker script (Script 1F) to find the real styled element.
- **"Logos are missing"** → They're data-URI CSS backgrounds, not `<img>` tags. Use Script 7.
- **Save Paths:** Always use **absolute paths** for saving screenshots and assets.
- **Zombie Browsers:** If the browser-use agent is stuck, try closing and reopening the tab via `tabs_context`.

---
**Ethical/Legal Note:** When cloning websites, ensure you have the appropriate permissions. For learning purposes, focus on reverse-engineering the structural layout and design systems (spacing, colors, typography) rather than ripping proprietary copy, branding, or gated assets.