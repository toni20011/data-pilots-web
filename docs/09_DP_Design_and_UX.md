# 09 — Design and UX

## Design system

All CSS lives inline in `<style>` blocks within each HTML file. There is no external stylesheet or CSS preprocessor. Every page includes the same `:root` token block.

---

## Colour tokens

```css
/* Background */
--navy:       #0B1929;   /* dark page background */
--navy-mid:   #112238;   /* slightly lighter navy, cards/nav */
--navy-soft:  #1A3350;   /* softest navy, subtle surfaces */

/* Accent */
--teal:       #00C8A8;   /* primary action colour */
--teal-dim:   rgba(0,200,168,.12);
--teal-border:rgba(0,200,168,.22);
--cyan:       #00AFCC;   /* gradient partner to teal */
--green:      #10B981;   /* success states */
--purple:     #8B5CF6;   /* secondary accent (Trust Panel) */
--blue:       #2C5AA0;

/* Text / neutral scale */
--slate-50:   #F8FAFC;   /* light page background */
--slate-100:  #F1F5F9;
--slate-200:  #E2E8F0;
--slate-400:  #94A3B8;   /* secondary text */
--slate-500:  #64748B;
--slate-600:  #475569;   /* body text on light pages */
--slate-800:  #1E293B;   /* primary text on light pages */
--white:      #FFFFFF;
```

---

## Typography

### Fonts loaded (all pages)
```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=DM+Serif+Display:ital@0;1&display=swap" rel="stylesheet"/>
```

**Both fonts must be in the `<link>` URL on every page.**

### Font usage rules

| Element | Font | Weight | Notes |
|---|---|---|---|
| Body / UI text | Inter | 300–700 | `font-family: 'Inter', system-ui, sans-serif` |
| Hero h1 | Inter | 900 | Intentional — maximum impact |
| Section h2 | DM Serif Display | 400 | `var(--font-display)` — editorial, not heavy |
| Pull-quotes / brand line | DM Serif Display | 400 italic | `font-style: italic` |
| Kickers / labels | Inter | 700 | uppercase, letter-spacing |
| Buttons | Inter | 600 | `font-family: inherit` |

```css
:root {
  --font-display: 'DM Serif Display', Georgia, serif;
}
```

**The DM Serif / Inter contrast is a core part of the brand character.** Section headings should be DM Serif 400 (light, editorial) not Inter 900 (heavy, blocky). This is the most common mistake when adding new pages.

---

## Page backgrounds

| Page type | Background |
|---|---|
| Marketing pages (index, panel) | `var(--navy)` — dark |
| About / content pages (about, framework, founder) | `var(--slate-50)` — light |

---

## Spacing and radii

```css
--r-sm: 8px;
--r-md: 12px;
--r-lg: 18px;
--r-xl: 24px;
```

Standard section padding: `80px 0` (top/bottom). Hero sections: `80px 0 100px` or similar.

---

## Animation system

All pages use a scroll-reveal animation:

```css
.reveal {
  opacity: 0;
  transform: translateY(20px);
  transition: opacity .5s var(--ease), transform .5s var(--ease);
}
.reveal.visible {
  opacity: 1;
  transform: translateY(0);
}
```

```javascript
const obs = new IntersectionObserver(entries => {
  entries.forEach(e => {
    if (e.isIntersecting) { e.target.classList.add('visible'); obs.unobserve(e.target); }
  });
});
document.querySelectorAll('.reveal').forEach(el => obs.observe(el));
```

Stagger delays use `.reveal-delay-1` (`transition-delay: .1s`), `.reveal-delay-2` (`.2s`), etc.

**Screenshot gotcha:** `.reveal` elements start at `opacity: 0`. Preview screenshots will show empty sections unless you force visibility first:
```javascript
document.querySelectorAll('.reveal').forEach(el => {
  el.classList.add('visible');
  el.style.opacity = '1';
  el.style.transform = 'none';
});
```

---

## Component patterns

### Section structure
```html
<section class="[name]-section" id="[anchor]">
  <div class="container">
    <div class="reveal" style="margin-bottom:XX;">
      <div class="section-kicker">Kicker text</div>
      <h2 class="[name]-h2">Section heading</h2>
      <p class="section-sub">Supporting line</p>
    </div>
    <!-- content -->
  </div>
</section>
```

### Kicker labels
Small uppercase label above section headings:
```css
.section-kicker { font-size: 11.5px; font-weight: 700; text-transform: uppercase; letter-spacing: .1em; color: var(--teal); margin-bottom: 12px; }
```

### Buttons

```css
/* Base */
.btn { display: inline-flex; align-items: center; gap: 7px; font-family: inherit; font-weight: 600; cursor: pointer; border: none; text-decoration: none; border-radius: var(--r-sm); }

/* Primary (teal gradient) */
.btn-teal { padding: 10px 22px; font-size: 13.5px; background: linear-gradient(135deg, var(--teal), var(--cyan)); color: var(--navy); }

/* Ghost (nav) */
.btn-ghost { padding: 9px 18px; font-size: 13.5px; color: rgba(255,255,255,.55); background: transparent; border: 1px solid rgba(255,255,255,.12); }
```

### Card surfaces (dark pages)
```css
background: rgba(255,255,255,.03);
border: 1px solid rgba(255,255,255,.07);
border-radius: var(--r-md);
```

### Card surfaces (light pages)
```css
background: var(--white);
border: 1px solid var(--slate-200);
border-radius: var(--r-xl);
```

### Pull-quote (brand line style)
```css
.wdp-brand-line {
  font-size: 16px;
  font-style: italic;
  color: rgba(255,255,255,.9);
  border-left: 3px solid var(--teal);
  padding-left: 14px;
  margin-top: 22px;
  line-height: 1.65;
  font-family: var(--font-display);
}
```

---

## Nav structure (all pages)

```html
<nav>
  <div class="container">
    <div class="nav-inner">
      <a href="/" class="logo">...</a>
      <ul>
        <li><a href="#results">How It Works</a></li>
        <li><a href="#pricing">Get Started</a></li>
        <li><a href="#faq">FAQ</a></li>
        <li class="nav-dropdown">
          <button class="nav-dd-btn" aria-expanded="false">
            Learn More <chevron-svg/>
          </button>
          <ul class="nav-dd-menu">
            <li><a href="about.html">About Data Pilots</a></li>
            <li><a href="panel.html">Trust Panel</a></li>
            <li><a href="framework.html">Our Framework</a></li>
            <div class="nav-dd-sep"></div>
            <li><a href="#proof">Get Involved <span class="nav-dd-tag">↓ this page</span></a></li>
          </ul>
        </li>
      </ul>
      <div class="nav-actions">
        <a href="#pricing" class="btn btn-ghost">Get Access</a>
        <a href="#hero-scan" class="btn btn-teal">Take the Snapshot</a>
      </div>
    </div>
  </div>
</nav>
```

**Dropdown CSS note:** `nav ul { display: flex }` applies to ALL nested `ul` elements. The `.nav-dd-menu` requires `display: block !important` to override this and stack items vertically.

---

## Known limitations / pending

- **Logo:** Wordmark only — no icon/symbol logo yet
- **Mobile nav:** Hamburger menu not yet implemented (nav links hidden on mobile)
- **Community form:** Currently `mailto:` fallback — Brevo not yet wired up
- **trust-ecosystem.html:** Does not yet have DM Serif Display in its font load
