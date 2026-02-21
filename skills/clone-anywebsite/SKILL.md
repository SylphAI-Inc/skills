---
name: clone-anywebsite
description: Guide and recipe for high-fidelity, visual-first web cloning mainly using the Chrome DevTools MCP and Deep DOM Interrogation. and screenshot and read image tool
author: SylphAI-Inc
version: 1.0.0
---

# Guide: Visual-First Web Cloning Recipe

When building a high-fidelity landing page clone, the biggest trap is relying purely on DOM trees and CSS dumps. Modern website builders (Framer, Webflow) generate deeply nested "div soup" and obfuscated CSS to create visual effects. 

**The Golden Rule:** Trust your "eyes" (screenshots) first, but when an effect looks too complex to be pure CSS, use **Deep DOM Interrogation** to steal the exact asset.

## The 80/20 Cloning Philosophy
To clone efficiently, you must divide your workflow into two distinct phases so you don't get bogged down pixel-pushing too early:

1. **The 80% Sprint (Speed & Structure):** Get the page laid out rapidly. Use Steps 0-2 to fetch the semantic HTML, scaffold the React component tree (`Navbar`, `Hero`, `Features`), and apply basic Tailwind classes for layout (Flex/Grid) and spacing. Accept approximations here—use solid colors instead of complex gradients, standard CSS shadows, and static backgrounds. **Move fast.**
2. **The 20% Polish (Pixel Perfection & Physics):** Once the 80% structure is on screen, shift gears to meticulous engineering. Use Steps 3-5 to steal the exact math. This is where you use "Sniper CSS" to extract exact multi-stop gradients, rip WebGL canvas backgrounds to `.webm` videos, map massive multi-layer box-shadows, and implement Framer Motion spring physics.

---

## The 6-Step "Visual-First" Recipe

### Step 0: Codebase Scaffolding Strategy
Before writing code, establish a scalable folder structure. Modern landing pages should be componentized.
*   **`src/components/layout/`**: `Navbar.tsx`, `Footer.tsx` (Global elements)
*   **`src/components/sections/`**: `Hero.tsx`, `Features.tsx`, `Testimonials.tsx` (Page blocks)
*   **`src/components/ui/`**: `Button.tsx`, `GlassCard.tsx` (Reusable micro-components)
*   **`src/assets/media/`**: Local storage for extracted videos, noise overlays, and icons.

### Step 1: The "Eye Test" (Visual Grounding)
**Before looking at a single line of code, visually ground yourself in the reference site.**

1. **Capture:** Navigate to the target site and take a screenshot using an absolute path.
   `mcp_chrome-devtools_take_screenshot(filePath="/absolute/path/to/ref.png")`
2. **Analyze:** Read the image (`LocalFileOps_read_image`) and actively identify the *Vibe*:
   - **Backgrounds:** Is it flat? A subtle radial gradient? Are there sweeping SVG waves or floating blurred orbs?
   - **Buttons:** Are they flat? Glassmorphic (backdrop-blur)? Do they have glowing auras?
   - **Typography:** Which specific words are highlighted? Are there gradient text clips?

### Step 2: Macro Structure Capture (Playwright/DOM Snapshot)
*Best for: Getting the general layout semantic HTML structure (Nav, Hero, Bento Grid, Footer).*

- Take a DOM text snapshot using Chrome DevTools or Playwright to understand the section-by-section flow and extract the actual copy/text.
- **Do not blindly copy the DOM.** Distill the complicated nested builder divs into clean, semantic React (e.g., `<section>`, `<nav>`, `<ul>`).

### Step 3: Micro Extraction (Sniper CSS)
*Best for: Extracting exact pixel-perfect design tokens during the 20% Polish.*

**Tool to use:** `mcp_chrome-devtools_evaluate_script`

**Do NOT query the full `getComputedStyle` object.** It returns 500+ properties, overwhelms the context window, and creates hallucination/confusion. Instead, use targeted JS payloads to extract exactly what you need.

**Script 1: Typography Tokens (Fonts, Spacing, Weights)**
*Why: To perfectly match headings. Used to discover that Calisto's H1 used `-4.8px` letter spacing and specific gray/blue hex colors.*
```javascript
() => {
  const el = document.querySelector('h1');
  const s = window.getComputedStyle(el);
  return JSON.stringify({ 
    color: s.color, 
    fontSize: s.fontSize,
    fontWeight: s.fontWeight,
    letterSpacing: s.letterSpacing,
    lineHeight: s.lineHeight
  }, null, 2);
}
```

**Script 2: Bounding Box & Overflow (The Glow/Shadow Check)**
*Why: To find exact dimensions and see if glowing effects bleed outside the element. We used this to realize the Hero button was exactly 160x160px with `overflow: visible`, allowing inner conic gradients to blur outside the borders.*
```javascript
() => {
  const btn = Array.from(document.querySelectorAll('a')).find(l => l.textContent.includes('Get Started'));
  if (!btn) return "Not found";
  const rect = btn.getBoundingClientRect();
  const s = window.getComputedStyle(btn);
  
  return JSON.stringify({
    width: rect.width,
    height: rect.height,
    display: s.display,
    borderRadius: s.borderRadius,
    overflow: s.overflow,
    boxShadow: s.boxShadow
  }, null, 2);
}
```

**Script 3: Glassmorphism & Backgrounds**
*Why: To grab exact transparency, blur, and gradient values for navbars or cards.*
```javascript
() => {
  const el = document.querySelector('nav');
  const s = window.getComputedStyle(el);
  return JSON.stringify({
    background: s.background,
    backdropFilter: s.backdropFilter,
    border: s.border
  }, null, 2);
}
```

**Script 4: Typography & Forced Line-Breaks**
*Why: A clone looks instantly fake if text wraps differently than the original. Don't let the browser decide fluidly. Extract exact container widths to force identical line breaks.*
```javascript
() => {
  const el = document.querySelector('h1');
  const r = el.getBoundingClientRect();
  return JSON.stringify({ 
    containerMaxWidth: r.width // Use this in Tailwind (e.g., max-w-[900px]) to force exact wraps!
  }, null, 2);
}
```

**Script 5: Abstract Glows & "Orbits" (The Glow Fallacy)**
*Why: A common trap is seeing a background aura and guessing it's a simple radial gradient with a massive `blur()`. High-end templates actually use hard shapes, multi-stop linear gradients, precise matrix transforms (rotations), and specific blend modes with a very tight blur. Eyeballing this turns a sharp "galaxy arm" into a muddy blob.*
```javascript
() => {
  const el = document.querySelector('[data-framer-name="Big Circle"]'); 
  if (!el) return "Not found";
  const s = window.getComputedStyle(el);
  return JSON.stringify({
    background: s.background, // Captures complex multi-stop gradients
    transform: s.transform,   // Captures crucial rotation angles
    filter: s.filter,         // Captures the exact, often surprisingly small, blur
    opacity: s.opacity
  }, null, 2);
}
```

### Step 4: Deep DOM Interrogation (The Secret Sauce)
*Best for: Replicating complex glows, overlapping animations, and fluid backgrounds.*

When an effect (like a smooth background or a swirling button) is too complex, **do not guess the math**. Framer and Webflow hide these in layered divs, pseudo-elements, or literal `<video>`/`<canvas>` tags. 

**Script 1: Render Engine Identification (Video vs Canvas vs CSS)**
If the background is moving fluidly, you must determine *what* is rendering it before trying to clone it. Find the full-screen background node:
```javascript
() => {
  const backgrounds = [];
  document.querySelectorAll('*').forEach(el => {
    const style = window.getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    // Look for large elements spanning >80% of screen in the background
    if ((style.position === 'fixed' || style.position === 'absolute') && 
        (parseInt(style.zIndex) <= 0 || style.zIndex === 'auto') && 
        rect.width >= window.innerWidth * 0.8 &&
        rect.height >= window.innerHeight * 0.5 &&
        el.tagName !== 'BODY' && el.tagName !== 'HTML') {
       backgrounds.push({ tag: el.tagName, html: el.outerHTML.substring(0, 300) });
    }
  });
  return JSON.stringify(backgrounds, null, 2);
}
```
*Lesson:* The DOM never lies. You might discover the "complex animation" is actually:
1.  **A Video:** A `<video src="...mp4">` tag (like in the Calisto template). *Solution: Extract the URL and drop it in.*
2.  **A WebGL Canvas:** A `<canvas data-paper-shaders="true">` tag (like in the Portfolite template). *Solution: Do not hack CSS. Scaffold React Three Fiber and write a GLSL shader. See Script 3.*
3.  **A Noise Overlay:** A repeating film-grain image (`background-image: url(...noise.png)`) at 5-10% opacity layered over the effect to prevent color banding.

**Script 2: Deep Extraction for UI Micro-Components (`outerHTML`)**
To clone a complex modern button or pill badge, do not guess the CSS. Builders use massive multi-layered `box-shadow` strings (e.g., 6 layers of shadow) and precise `rgba` borders to create glowing depth. Extract its literal nested structure:
```javascript
() => {
  const btn = Array.from(document.querySelectorAll('a')).find(l => l.textContent.includes('Get Started'));
  return btn ? btn.parentElement.outerHTML : 'Not found';
}
```
*Lesson:* This reveals the nested `conic-gradient` divs, `blur()` filters, and massive `box-shadow` arrays. Map those literal strings directly into an arbitrary Tailwind class like `shadow-[0px_0.7px_..._rgba(...)]`.

**Script 3: The API Interceptor (Shader Stealer)**
If the target is using a WebGL `<canvas>`, the exact GLSL shader code is often minified in JS chunks. You can hijack the browser's WebGL API to intercept the raw shader math before it goes to the GPU.
Inject this script *before* the page loads (using `initScript` in `mcp_chrome-devtools_navigate_page`):
```javascript
window.__interceptedShaders = [];
function hookContext(glPrototype) {
  if (!glPrototype) return;
  const originalShaderSource = glPrototype.shaderSource;
  glPrototype.shaderSource = function(shader, source) {
    window.__interceptedShaders.push(source);
    originalShaderSource.call(this, shader, source);
  };
}
hookContext(WebGLRenderingContext.prototype);
if (typeof WebGL2RenderingContext !== 'undefined') hookContext(WebGL2RenderingContext.prototype);
```
Then, evaluate `JSON.stringify(window.__interceptedShaders)` to read the exact GLSL math!

**Script 4: The "Last Resort" Canvas Recorder**
When a WebGL Canvas shader is too heavily obfuscated to intercept (or relies on proprietary 3D math engines), do not try to guess the GLSL math. Instead, literally record the GPU output directly from the reference site and use it as a seamless background video.
```javascript
() => {
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
      a.href = url;
      a.download = 'framer_perfect_loop.webm';
      document.body.appendChild(a);
      a.click(); // Triggers the download
      document.body.removeChild(a);
      resolve("Recorded 8s and downloaded: framer_perfect_loop.webm");
    };

    recorder.start();
    setTimeout(() => recorder.stop(), 8000); // 8 seconds for a good loop
  });
}
```

### Step 5: Synthesis & Rebuild (Tailwind + Framer Motion)
*Best for: Translating visual effects into clean, modern tech stacks.*

1. **Build the Base (The 80%):** Scaffold the structure using Step 2.
2. **Apply Tokens (The 20%):** Plug in the exact colors, typography, and spacing from Step 3.
3. **Entrance Physics (The 20%):** Use `framer-motion` for buttery smooth spring entrances instead of standard CSS transitions.
4. **Recreate the "Vibe":** 
   - *Videos/Canvas:* Drop the extracted `<video>` tag directly into an absolute background container.
   - *Framer Glows/Auras:* Use layered absolute divs with exact gradient/blur tokens.
5. **Verify (The Two-Tab & Stitch Workflow):** 
   - **Two Tabs:** Keep the reference site and your local clone open in separate MCP browser tabs.
   - **CRITICAL - Explicit Page Selection:** When juggling multiple tabs, taking a screenshot without focusing the tab will capture the wrong page or stale state. You MUST follow this exact sequence:
     1. `mcp_chrome-devtools_list_pages` to get the `pageId` for both tabs.
     2. `mcp_chrome-devtools_select_page(pageId=REF_ID)` to explicitly focus the reference.
     3. Take the reference screenshot with an absolute path (`ref_latest.png`).
     4. `mcp_chrome-devtools_select_page(pageId=LOCAL_ID)` to explicitly focus your local clone.
     5. *(Optional but recommended)* Run `location.reload()` via script if WebGL or HMR is stuck.
     6. Take the local screenshot with an absolute path (`local_latest.png`).
   - **Side-by-Side Stitching:** Use a quick Python script via `BashTool` to stitch them together horizontally for a flawless 1:1 visual comparison:
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
   - **Read:** Use `LocalFileOps_read_image` on `combined.png` to spot any remaining visual discrepancies side-by-side.

## Troubleshooting & Best Practices

- **"The background animation is missing!"** -> You assumed it was CSS. Run the Background Media script (Step 4) to find the hidden `<video>` or `<canvas>` tag.
- **"The Button looks totally different!"** -> Extract the `outerHTML` of the button's parent. You likely missed overlapping blurred divs or 6-layer box shadows that create the glow effect.
- **"The Text Wraps Wrong!"** -> You let the browser decide fluidly. Extract the exact bounding box width from the original and hardcode it (`max-w-[...]`).
- **Save Paths:** Always use **Absolute Paths** for saving screenshots to avoid losing them in the MCP server's hidden working directories.
- **Zombie Browsers:** If the DevTools server fails with a lock error, run `pkill -f "chrome-devtools-mcp" || true`.

---
**Ethical/Legal Note:** When cloning websites, ensure you have the appropriate permissions. For learning purposes, focus on reverse-engineering the structural layout and design systems (spacing, colors, typography) rather than ripping proprietary copy, branding, or gated assets.
