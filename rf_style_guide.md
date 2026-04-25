# 🎨 Guía de Estilo — Control RF (App)

Extraída de `styles.css`, `base.html` y `login.html` para migración pura de estilo.

---

## 1. Fuentes (Typography)

### Fuentes principales
| Zona | Fuente | Pesos | CDN |
|---|---|---|---|
| **App principal** | `Outfit` | 300, 400, 600, 700 | `https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap` |
| **Login** | `Inter` | 300, 400, 500, 600, 700 | `https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap` |

### Tipografía aplicada
```css
body {
    font-family: 'Outfit', sans-serif;  /* App principal */
}

/* Login page usa: */
body { font-family: 'Inter', sans-serif; }
```

### Escalas de tamaño tipográfico
```css
.fs-xxs    { font-size: 0.65rem; }
.fs-xs     { font-size: 0.75rem; }
.fs-tiny   { font-size: 0.6rem;  }
.fs-medium { font-size: 1.1rem;  }
.fs-large  { font-size: 1.2rem;  }
.fs-giant  { font-size: 2.2rem;  }
```

### Weight & Tracking
```css
h1, h2, h3, h4, h5, h6 { font-weight: 700 !important; }
.tracking-wide { letter-spacing: 1px; }
/* Headings suelen usar letter-spacing: -1.5px (tracking negativo) */
```

---

## 2. Paleta de Colores

### 🌙 Tema Oscuro (Default — "Matte Charcoal")

```css
:root {
    /* ── Accent Principal — Muted Sage Teal ── */
    --primary-calipso:     #6b8e8e;
    --primary-calipso-rgb: 107, 142, 142;
    --primary-dark:        #4d6666;
    --accent-info:         #6b8e8e;

    /* ── Fondos ── */
    --bg-main:     #1a1a1b;            /* Fondo principal */
    --bg-sidebar:  #151516;            /* Sidebar (gris oscuro sólido) */
    --bg-navbar:   #1a1a1b;            /* Navbar */
    --bg-card:     rgba(255, 255, 255, 0.03); /* Cards glassmorphism */

    /* ── Textos ── */
    --text-main:    #e2e8f0;           /* Texto principal (Slate 200) */
    --text-muted:   #a1a1aa;           /* Texto secundario (Zinc 400) */
    --text-heading: #ffffff;           /* Headings (blanco puro) */

    /* ── Bordes ── */
    --border-glass:   rgba(255, 255, 255, 0.04);
    --sidebar-border: rgba(255, 255, 255, 0.02);
    --nav-border:     rgba(255, 255, 255, 0.02);
}
```

### ☀️ Tema Claro

```css
[data-theme="light"] {
    --bg-main:        #dae1e7;
    --bg-sidebar:     linear-gradient(180deg, #ffffff 0%, #e2e8f0 100%);
    --bg-navbar:      #ffffff;
    --bg-card:        #ffffff;
    --text-main:      #1e293b;         /* Dark Slate 800 */
    --text-muted:     #475569;         /* Slate 600 */
    --text-heading:   #0f172a;         /* Dark Slate 900 */
    --border-glass:   rgba(0, 0, 0, 0.15);
    --sidebar-border: rgba(0, 0, 0, 0.1);
    --nav-border:     rgba(0, 0, 0, 0.1);
}
```

### 🔶 Paleta Login (Copper/Ocre)
```css
:root {
    --copper:      #c27c3a;
    --copper-lt:   #d9924f;
    --copper-xlt:  #e8ad78;
    --copper-glow: rgba(194, 124, 58, 0.30);
    --dark:        #110d09;
    --dark-2:      #1a1208;
    --card-bg:     #1f1610;
    --card-border: #3a2a1a;
    --input-bg:    #150f08;
    --text:        #ede0d0;
    --muted:       #9a7e65;
    --placeholder: #5c4530;
}
```

### Colores semánticos / estados
| Rol | Color | Uso |
|---|---|---|
| **Success** | `#2fb344` | Status "Cerrado", badges verdes |
| **Danger** | `#dc3545` (Bootstrap) | Botón "Salir", alertas |
| **Warning / Overdue** | `#ff851b` | Vencimientos, alertas naranjas |
| **Theme Toggle Sun** | `#f59e0b` (Amber) | Ícono sol en modo claro |
| **Muted Sage (light info)** | `#5a7d7d` | `.text-info` en modo claro |

---

## 3. Glassmorphism & Efectos

### Glass Card
```css
.glass-card {
    background: var(--bg-card);
    -webkit-backdrop-filter: blur(8px);
    backdrop-filter: blur(8px);
    border: 1px solid var(--border-glass);
    border-radius: 20px;
    transition: all 0.3s ease;
}

.glass-card:hover {
    border-color: rgba(107, 142, 142, 0.15);  /* --primary-calipso-rgb */
}
```

### Login Card (Glassmorphism fuerte)
```css
.login-card {
    background: rgba(26, 18, 8, 0.45);
    -webkit-backdrop-filter: blur(24px) saturate(150%);
    backdrop-filter: blur(24px) saturate(150%);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 22px;
    box-shadow:
        0 0 0 1px rgba(255, 255, 255, 0.025),
        0 30px 70px rgba(0, 0, 0, 0.65),
        0 0 80px rgba(194, 124, 58, 0.25);   /* Halo glow */
}
```

### Backgrounds con gradiente sutil
```css
.card-glass-dark     { background: rgba(255, 255, 255, 0.02); }
.card-glass-gradient { background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 100%); }

/* SIGO card dark */
background: linear-gradient(145deg, rgba(30, 30, 31, 0.9), rgba(20, 20, 21, 0.95));
```

---

## 4. Sombras (Shadows)

```css
/* Navbar */
box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3);

/* Sidebar */
box-shadow: 10px 0 30px rgba(0, 0, 0, 0.1);

/* Logo container */
box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);

/* Logo hover glow */
box-shadow: 0 6px 20px rgba(0, 206, 209, 0.3);

/* Active menu item */
box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);

/* Dropdown */
box-shadow: 0 10px 40px rgba(0, 0, 0, 0.8);

/* Hover elevación */
box-shadow: 0 15px 35px rgba(0, 0, 0, 0.4);

/* Login button */
box-shadow: 0 4px 22px rgba(184, 107, 37, 0.45);

/* Light mode cards */
box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
```

---

## 5. Border Radius

| Elemento | Radius |
|---|---|
| Cards principales | `20px` |
| Login card | `22px` |
| Menu items | `12px` |
| Inputs | `10px` |
| Logo containers | `12px – 14px` |
| Dropdowns | `12px` |
| Dropdown items | `8px` |
| Badges | `4px` |
| Scrollbar thumb | `10px` |

---

## 6. Transiciones & Animaciones

### Curvas de animación (Easing)
```css
/* Standard */
transition: all 0.3s ease;

/* Premium — usada en sidebar y menú */
transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);

/* Menú RF items */
transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

/* Module logo bounce */
transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);

/* SIGO card smooth */
transition: all 0.4s cubic-bezier(0.165, 0.84, 0.44, 1);

/* Body theme change */
transition: background-color 0.3s ease, color 0.3s ease;
```

### Hover Effects
```css
/* Elevación Y */
.hover-translate-y:hover {
    transform: translateY(-8px);
    box-shadow: 0 15px 35px rgba(0, 0, 0, 0.4);
}

/* SIGO card */
.sigo-card:hover {
    transform: translateY(-4px);
}

/* Logo rotación */
.module-logo-container:hover {
    transform: rotate(2deg) scale(1.1);
}

/* Menú lateral desplazamiento */
.rf-menu-item:hover {
    transform: translateX(5px);
}

/* Dropdown items */
.dropdown-item:hover {
    transform: translateX(3px);
}

/* Login card entrada */
@keyframes slideUp {
    from { opacity: 0; transform: translateY(32px); }
    to   { opacity: 1; transform: translateY(0); }
}
animation: slideUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) both;
```

### Progress Ring
```css
.progress-ring-circle { transition: stroke-dashoffset 1.5s ease-out; }
```

---

## 7. Scrollbar Personalizado

```css
::-webkit-scrollbar {
    width: 6px;
}
::-webkit-scrollbar-track {
    background: rgba(0, 0, 0, 0.1);
}
::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 10px;
}
::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.1);
}
```

---

## 8. Formularios & Inputs

### Dark Mode
```css
.form-control {
    background-color: rgba(255, 255, 255, 0.05);
    border-color: rgba(255, 255, 255, 0.1);
    color: var(--text-main);
}

.form-control:focus {
    background-color: rgba(255, 255, 255, 0.08);
    border-color: var(--primary-calipso);
    box-shadow: 0 0 0 0.25rem rgba(107, 142, 142, 0.25);
}
```

### Login (Copper Theme)
```css
.form-input {
    background: rgba(21, 15, 8, 0.5);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 10px;
    color: #ede0d0;
}

.form-input:focus {
    border-color: #c27c3a;
    box-shadow: 0 0 0 3px rgba(194, 124, 58, 0.30);
}
```

---

## 9. Botones Principales

### Botón Login (Gradient Copper)
```css
.btn-login {
    background: linear-gradient(135deg, #b86b25 0%, #d4864a 60%, #c27c3a 100%);
    border: none;
    border-radius: 10px;
    font-weight: 600;
    color: #fff;
    box-shadow: 0 4px 22px rgba(184, 107, 37, 0.45);
    letter-spacing: 0.2px;
}

.btn-login:hover {
    opacity: 0.9;
    transform: translateY(-1px);
    box-shadow: 0 8px 30px rgba(184, 107, 37, 0.55);
}
```

### Botón Info (Teal)
```css
.btn-info {
    background-color: #6b8e8e;
    color: white;
    border-color: #4d6666;
}
```

---

## 10. Alertas (Login)

```css
.alert-danger  { background: rgba(220,60,40,.12);  color: #f8a090; border: 1px solid rgba(220,60,40,.25);  }
.alert-success { background: rgba(40,180,90,.10);   color: #86efac; border: 1px solid rgba(40,180,90,.22);  }
.alert-warning { background: rgba(220,160,30,.10);  color: #fde68a; border: 1px solid rgba(220,160,30,.22); }
.alert-info    { background: rgba(60,140,200,.10);   color: #93c5fd; border: 1px solid rgba(60,140,200,.22); }
```

---

## 11. Dropdown (Dark Mode)

```css
.dropdown-menu {
    background-color: #1e1e1f;
    border: 1px solid rgba(255, 255, 255, 0.15);
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.8);
    backdrop-filter: none;     /* Sin blur para evitar fuzzyness */
    border-radius: 12px;
    padding: 8px;
}

.dropdown-item {
    color: #ffffff;
    border-radius: 8px;
    padding: 10px 16px;
    font-weight: 500;
}

.dropdown-item:hover {
    background-color: rgba(107, 142, 142, 0.15);
    color: #6b8e8e;
    transform: translateX(3px);
}
```

---

## 12. Active Link / Menú Lateral

```css
/* Indicador visual: barra lateral brillante */
.rf-menu-item.active-link::before {
    content: '';
    position: absolute;
    left: 0;
    top: 20%;
    height: 60%;
    width: 4px;
    background: #6b8e8e;
    border-radius: 0 4px 4px 0;
    box-shadow: 0 0 10px #6b8e8e;    /* Glow effect */
}

.rf-menu-item.active-link {
    background: rgba(107, 142, 142, 0.12);
    border: 1px solid rgba(107, 142, 142, 0.3);
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
}
```

---

## 13. Dependencias externas

```html
<!-- Bootstrap 5.3 -->
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>

<!-- Font Awesome 6.4 (íconos) -->
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">

<!-- Bootstrap Icons (solo en login) -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">

<!-- Google Fonts -->
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
```

---

## 14. Sistema de Temas (JavaScript)

```javascript
// Guardar preferencia en localStorage, aplicar con data-attribute
const currentTheme = localStorage.getItem("theme") || "dark";

const setTheme = (theme) => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
    // Cambiar ícono moon ↔ sun
};

// Toggle: dark ↔ light
themeToggle.addEventListener("click", () => {
    const newTheme = document.documentElement.getAttribute("data-theme") === "dark"
        ? "light" : "dark";
    setTheme(newTheme);
});
```

> El tema se aplica con `[data-theme="light"]` en CSS. El default es dark (sin atributo o `data-theme="dark"`).

---

## 15. Resumen Visual Rápido

| Propiedad | Valor |
|---|---|
| **Estética** | Matte Charcoal + Glassmorphism |
| **Fuente App** | Outfit (300–700) |
| **Fuente Login** | Inter (300–700) |
| **Accent principal** | `#6b8e8e` (Muted Sage Teal) |
| **Accent login** | `#c27c3a` (Copper) |
| **Fondo oscuro** | `#1a1a1b` |
| **Fondo claro** | `#dae1e7` |
| **Cards** | Glass con blur 8px, border-radius 20px |
| **Animaciones** | cubic-bezier premium, translateY/X hovers |
| **Scrollbar** | 6px, ultra-sutil |
| **Íconos** | Font Awesome 6.4 + Bootstrap Icons |
| **Framework CSS** | Bootstrap 5.3 |
| **Tema** | Dual (dark/light) via `data-theme` + localStorage |
