# Unified Interaction System (Deep Blue) – Implementation Plan

## 🎯 Objective
Standardize hover, focus, and active states across the dashboard using the Deep Blue system while preserving data color integrity.

---

## 🧩 Step 1: Define Global Tokens (index.css)

Add to :root:

```css
:root {
  --bg: #f8fafc;
  --card: #ffffff;
  --border-soft: #e5e7eb;

  --brand: #2563eb;
  --brand-strong: #1d4ed8;
  --brand-soft: rgba(37, 99, 235, 0.12);

  --focus-ring: rgba(37, 99, 235, 0.35);
}
```

---

## 🧱 Step 2: Match Row States

```css
.match-row {
  background: var(--card);
  border: 1px solid var(--border-soft);
  transition: all 0.2s ease;
}

/* Hover */
.match-row:hover {
  background: rgba(37, 99, 235, 0.04);
  border-color: var(--brand-soft);
}

/* Active / Expanded */
.match-row.expanded {
  border-left: 3px solid var(--brand);
  background: rgba(37, 99, 235, 0.06);
}
```

---

## 🧩 Step 3: League Header Alignment

```css
.league-header {
  border-left: 3px solid rgba(37, 99, 235, 0.35);
  border-bottom: 1px solid var(--border-soft);
}
```

---

## 🔘 Step 4: Control Buttons (Header / Filter Bar)

```css
.control-btn {
  color: var(--text-muted);
  transition: all 0.2s ease;
}

/* Hover */
.control-btn:hover {
  background: rgba(37, 99, 235, 0.08);
}

/* Active */
.control-btn.active {
  background: var(--brand-soft);
  color: var(--brand);
}
```

---

## 🎯 Step 5: Focus States (Accessibility)

```css
:focus-visible {
  outline: 2px solid var(--focus-ring);
  outline-offset: 2px;
}
```

---

## ⚠️ Step 6: Protect Data Colors

DO NOT apply brand hover styles to:

- TIP badges
- 1X2 probability boxes
- XPTS boxes

Use neutral interaction instead:

```css
.prob-box:hover {
  filter: brightness(1.05);
}
```

---

## 🌙 Step 7: Dark Mode Adjustments

```css
body.dark {
  --brand-soft: rgba(37, 99, 235, 0.18);
  --focus-ring: rgba(96, 165, 250, 0.45);
}

/* Dark hover */
body.dark .match-row:hover {
  background: rgba(255,255,255,0.03);
}

/* Dark borders */
body.dark .match-row {
  border: none;
  border-bottom: 1px solid rgba(255,255,255,0.04);
}
```

---

## ⚡ Step 8: QA Checklist

- [ ] Hover is subtle (not competing with data)
- [ ] Active state clearly visible
- [ ] Focus ring works on all interactive elements
- [ ] No blue applied to data elements
- [ ] Dark mode hover is neutral (not blue)
- [ ] Borders consistent via --border-soft

---

## 🧠 Final Principle

Blue = Interaction  
Data colors = Meaning  

Never mix the two.
