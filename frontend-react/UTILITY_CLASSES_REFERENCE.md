# 🎨 Utility Classes Quick Reference

## Animation Classes

### Entry Animations
```css
.fade-in          /* Fade in from bottom with slide up */
.slide-in-left    /* Slide in from left side */
.slide-in-right   /* Slide in from right side */
.scale-in         /* Scale up from center */
```

**Usage:**
```jsx
<div className="fade-in">Content fades in smoothly</div>
<div className="slide-in-left">Slides in from left</div>
```

---

### Continuous Animations
```css
.pulse            /* Gentle pulsing opacity effect */
.glow             /* Glowing box-shadow effect */
.bounce           /* Bouncing up and down */
.breathe          /* Scale breathing effect */
```

**Usage:**
```jsx
<div className="pulse">Pulsing indicator</div>
<button className="glow">Glowing button</button>
```

---

### Loading Animations
```css
.shimmer          /* Shimmer loading effect */
.skeleton         /* Skeleton screen with shine */
.spinner-glow     /* Glowing spinner */
```

**Usage:**
```jsx
{loading ? (
  <div className="skeleton" style={{ width: '200px', height: '40px' }} />
) : (
  <div>Actual content</div>
)}
```

---

## Effect Classes

### Glass Effects
```css
.glass            /* Light glassmorphism */
.glass-dark       /* Dark glassmorphism */
```

**Properties:**
- Semi-transparent background
- Backdrop blur
- Subtle border
- Modern appearance

**Usage:**
```jsx
<div className="glass p-4 rounded">
  Glass morphism card
</div>
```

---

### Shadow Effects
```css
.shadow-premium   /* Multi-layered premium shadow */
```

**Usage:**
```jsx
<div className="shadow-premium">
  Enhanced shadow depth
</div>
```

---

### Text Effects
```css
.text-gradient    /* Gradient text (blue to purple) */
```

**Usage:**
```jsx
<h1 className="text-gradient">Gradient Heading</h1>
```

---

## Transition Classes

### Speed Controls
```css
.transition-smooth   /* Standard smooth transition */
.transition-spring   /* Bouncy spring transition */
```

**Usage:**
```jsx
<div className="transition-smooth hover:scale-110">
  Smooth transitions
</div>
```

---

### Interactive Effects
```css
.hover-lift       /* Lift up on hover */
```

**Usage:**
```jsx
<div className="hover-lift">
  Lifts when you hover
</div>
```

---

## Component Classes

### Cards
```css
.dashboard-card   /* Enhanced dashboard card */
.insight-card     /* Analytics/insight card */
.analytics-card   /* Statistics card */
.price-hero-card  /* Main price display card */
```

**Features:**
- Glassmorphism background
- Enhanced shadows
- Hover effects
- Smooth animations

**Usage:**
```jsx
<Card className="dashboard-card">
  <Card.Body>Content</Card.Body>
</Card>
```

---

### Status Indicators
```css
.status-indicator      /* Base status dot */
.status-indicator.live /* Green pulsing dot */
```

**Usage:**
```jsx
<span className="status-indicator live"></span>
<span className="ms-2">Live</span>
```

---

## Background Classes

```css
.bg-premium       /* Purple gradient background */
.bg-dark-premium  /* Dark gradient background */
```

**Usage:**
```jsx
<div className="bg-premium text-white p-4">
  Premium background
</div>
```

---

## Badge Classes

```css
.badge            /* Enhanced base badge */
.badge-success    /* Green gradient badge */
.badge-danger     /* Red gradient badge */
.badge-warning    /* Amber gradient badge */
.badge-info       /* Blue gradient badge */
.badge-primary    /* Purple gradient badge */
```

**Features:**
- Gradient backgrounds
- Hover scale effect
- Shadow depth
- Uppercase text

**Usage:**
```jsx
<span className="badge badge-success">Active</span>
<span className="badge badge-warning">Pending</span>
```

---

## Button Enhancements

### Auto-Applied to Bootstrap Buttons
```jsx
// Primary button with gradient
<Button variant="primary">Click Me</Button>

// Success button with gradient
<Button variant="success">Save</Button>

// Warning button with gradient
<Button variant="warning">Alert</Button>
```

**Features:**
- Gradient backgrounds
- Ripple effect on click
- Lift on hover
- Enhanced shadows

---

## Custom CSS Properties

### Use in Your Styles
```css
/* Colors */
var(--premium-blue)
var(--premium-purple)
var(--premium-gold)
var(--premium-emerald)
var(--premium-rose)

/* Spacing */
var(--space-xs)    /* 0.25rem */
var(--space-sm)    /* 0.5rem */
var(--space-md)    /* 1rem */
var(--space-lg)    /* 1.5rem */
var(--space-xl)    /* 2rem */

/* Border Radius */
var(--radius-sm)   /* 8px */
var(--radius-md)   /* 12px */
var(--radius-lg)   /* 16px */
var(--radius-xl)   /* 20px */
var(--radius-full) /* 9999px */

/* Shadows */
var(--shadow-sm)
var(--shadow-md)
var(--shadow-lg)
var(--shadow-xl)
var(--shadow-2xl)

/* Transitions */
var(--transition-fast)  /* 150ms */
var(--transition-base)  /* 250ms */
var(--transition-slow)  /* 350ms */
```

**Usage:**
```css
.my-component {
  background: var(--premium-blue);
  padding: var(--space-lg);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  transition: all var(--transition-base);
}
```

---

## Animation Keyframes Available

```css
@keyframes fadeIn          /* Fade in with slide up */
@keyframes slideInLeft     /* Slide from left */
@keyframes slideInRight    /* Slide from right */
@keyframes scaleIn         /* Scale from center */
@keyframes pulse           /* Opacity pulsing */
@keyframes shimmer         /* Shimmer sweep */
@keyframes skeletonShine   /* Skeleton shine sweep */
@keyframes spin            /* 360° rotation */
@keyframes spinnerGlow     /* Spinning with glow */
@keyframes glow            /* Box-shadow glow */
@keyframes bounce          /* Bounce animation */
@keyframes breathe         /* Scale breathing */
@keyframes valueChange     /* Value update animation */
@keyframes gradientFlow    /* Background gradient flow */
@keyframes overlayPulse    /* Overlay opacity pulse */
@keyframes particlesFloat  /* Floating particles */
@keyframes heroGlow        /* Hero card glow */
```

**Custom Animation Example:**
```css
.my-element {
  animation: fadeIn 0.6s ease-out;
}

.my-glow {
  animation: glow 2s infinite;
}
```

---

## Skeleton Loading Pattern

### Basic Skeleton
```jsx
<div className="skeleton" style={{ 
  width: '200px', 
  height: '20px',
  borderRadius: '6px'
}} />
```

### Skeleton Card
```jsx
<Card>
  <Card.Body>
    <div className="skeleton mb-2" style={{ width: '60%', height: '24px' }} />
    <div className="skeleton mb-2" style={{ width: '100%', height: '16px' }} />
    <div className="skeleton" style={{ width: '80%', height: '16px' }} />
  </Card.Body>
</Card>
```

---

## Responsive Utilities

### Staggered Animations
```css
.grid-item:nth-child(1) { animation-delay: 0.1s; }
.grid-item:nth-child(2) { animation-delay: 0.2s; }
.grid-item:nth-child(3) { animation-delay: 0.3s; }
/* etc. */
```

**Usage:**
```jsx
<div className="dashboard-grid">
  <div className="grid-item fade-in">First (0.1s delay)</div>
  <div className="grid-item fade-in">Second (0.2s delay)</div>
  <div className="grid-item fade-in">Third (0.3s delay)</div>
</div>
```

---

## Combining Classes

### Example 1: Premium Card
```jsx
<div className="glass shadow-premium hover-lift transition-smooth p-4 rounded">
  <h3 className="text-gradient">Premium Content</h3>
  <p>Beautiful card with multiple effects</p>
</div>
```

### Example 2: Animated Button
```jsx
<button className="btn btn-primary glow pulse">
  Attention-grabbing button
</button>
```

### Example 3: Loading State
```jsx
{loading ? (
  <div className="fade-in">
    <div className="skeleton mb-3" style={{ width: '100%', height: '40px' }} />
    <div className="skeleton mb-3" style={{ width: '80%', height: '20px' }} />
    <div className="skeleton" style={{ width: '60%', height: '20px' }} />
  </div>
) : (
  <div className="fade-in">
    {/* Actual content */}
  </div>
)}
```

---

## Performance Tips

### ✅ DO
- Use transform and opacity for animations (GPU accelerated)
- Combine utility classes for complex effects
- Use skeleton screens for better perceived performance
- Apply animations to specific elements, not entire pages

### ❌ DON'T
- Animate width/height (causes layout recalculation)
- Use too many simultaneous animations
- Apply heavy effects to frequently updating elements
- Forget to test on lower-end devices

---

## Browser Compatibility

All utility classes work on:
- ✅ Chrome/Edge (latest)
- ✅ Firefox (latest)
- ✅ Safari (latest)
- ✅ Mobile browsers

Some effects use:
- `backdrop-filter` (glassmorphism)
- `background-clip: text` (gradient text)
- CSS custom properties (variables)

---

## Quick Copy-Paste Examples

### Loading Spinner
```jsx
<div className="text-center py-5">
  <Spinner animation="border" className="spinner-glow" variant="primary" />
  <p className="mt-3 text-muted">Loading...</p>
</div>
```

### Status Badge
```jsx
<span className="badge badge-success">
  <i className="fas fa-check me-1"></i>
  Active
</span>
```

### Glowing Icon
```jsx
<div className="glow pulse" style={{
  width: '48px',
  height: '48px',
  background: 'linear-gradient(135deg, #f59e0b, #d97706)',
  borderRadius: '12px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center'
}}>
  <i className="fas fa-star text-white"></i>
</div>
```

### Premium Card
```jsx
<Card className="dashboard-card fade-in">
  <Card.Header className="bg-premium text-white">
    <i className="fas fa-chart-line me-2"></i>
    Analytics
  </Card.Header>
  <Card.Body>
    <p>Your content here</p>
  </Card.Body>
</Card>
```

---

## Need More?

Check out:
- **Full Documentation**: `UI_UX_ENHANCEMENTS.md`
- **Before/After**: `BEFORE_AND_AFTER.md`
- **Setup Guide**: `../SETUP_ENHANCED_UI.md`
- **Main README**: `README.md`

Happy styling! 🎨✨

