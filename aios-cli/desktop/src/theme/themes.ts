export type ThemeBase = 'dark' | 'light'

export interface ThemeSpec {
  id: string
  name: string
  base: ThemeBase
  bg: string
  chrome: string
  surface: string
  raised: string
  overlay: string
  border: string
  borderStrong: string
  text: string
  textSec: string
  textMuted: string
  accent: string
  accentHover: string
  success?: string
  danger?: string
  warning?: string
}

export interface ThemeDef {
  id: string
  name: string
  base: ThemeBase
  vars: Record<string, string>
}

export interface XtermTheme {
  background: string
  foreground: string
  cursor: string
  cursorAccent: string
  selectionBackground: string
  black: string
  red: string
  green: string
  yellow: string
  blue: string
  magenta: string
  cyan: string
  white: string
  brightBlack: string
  brightRed: string
  brightGreen: string
  brightYellow: string
  brightBlue: string
  brightMagenta: string
  brightCyan: string
  brightWhite: string
}

function expand(s: ThemeSpec): ThemeDef {
  const dark = s.base === 'dark'
  const accent = dark ? '#e5e5e5' : '#1a1a1a'
  const accentHover = dark ? '#ffffff' : '#000000'
  return {
    id: s.id,
    name: s.name,
    base: s.base,
    vars: {
      '--color-bg': s.bg,
      '--color-chrome': s.chrome,
      '--color-surface': s.surface,
      '--color-surface-raised': s.raised,
      '--color-surface-overlay': s.overlay,
      '--color-border': s.border,
      '--color-border-strong': s.borderStrong,
      '--color-text': s.text,
      '--color-text-secondary': s.textSec,
      '--color-text-muted': s.textMuted,
      '--color-accent': accent,
      '--color-accent-hover': accentHover,
      '--color-accent-soft': dark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.08)',
      '--color-success': s.success ?? (dark ? '#3fb950' : '#1a7f37'),
      '--color-danger': s.danger ?? (dark ? '#f0524a' : '#d1242f'),
      '--color-warning': s.warning ?? (dark ? '#d8a13a' : '#9a6700')
    }
  }
}

const SPECS: ThemeSpec[] = [
  {
    id: 'aios-dark', name: 'AIOS Dark', base: 'dark',
    bg: '#0b0b0e', chrome: '#101012', surface: '#141416', raised: '#1c1c20', overlay: '#242428',
    border: '#2a2a2e', borderStrong: '#3a3a3e',
    text: '#e3e3e6', textSec: '#a3a3ac', textMuted: '#6b6b72',
    accent: '#e5e5e5', accentHover: '#ffffff', success: '#3fb950', danger: '#f0524a', warning: '#d8a13a'
  },
  {
    id: 'aios-light', name: 'AIOS Light', base: 'light',
    bg: '#e8e8e8', chrome: '#dcdcdc', surface: '#e2e2e2', raised: '#d4d4d4', overlay: '#cacaca',
    border: '#c2c2c2', borderStrong: '#aeaeae',
    text: '#1d1d1d', textSec: '#4c4c4c', textMuted: '#6f6f6f',
    accent: '#1a1a1a', accentHover: '#000000'
  },
  {
    id: 'aios-cyberpunk', name: 'Cyberpunk', base: 'dark',
    bg: '#0a0a12', chrome: '#070710', surface: '#10101e', raised: '#171729', overlay: '#202037',
    border: '#202037', borderStrong: '#2f2f52',
    text: '#e6f0ff', textSec: '#8fa3c9', textMuted: '#5d6e94',
    accent: '#00e5ff', accentHover: '#4deeff', danger: '#ff2a6d', warning: '#ffd319'
  },
  {
    id: 'aios-minimal', name: 'Minimal', base: 'dark',
    bg: '#0a0a0a', chrome: '#101010', surface: '#141414', raised: '#1c1c1c', overlay: '#262626',
    border: '#262626', borderStrong: '#3a3a3a',
    text: '#fafafa', textSec: '#9e9e9e', textMuted: '#666666',
    accent: '#fafafa', accentHover: '#ffffff'
  },
  {
    id: 'aios-fox', name: 'Fox', base: 'dark',
    bg: '#160d0f', chrome: '#1d1012', surface: '#1c1214', raised: '#27181b', overlay: '#352024',
    border: '#33201f', borderStrong: '#4a2d2c',
    text: '#f5e4e6', textSec: '#c69ba0', textMuted: '#8d6468',
    accent: '#e23d5c', accentHover: '#ec5d77', danger: '#e23d5c'
  },
  {
    id: 'github-dark', name: 'GitHub Dark', base: 'dark',
    bg: '#0d1117', chrome: '#010409', surface: '#0d1117', raised: '#161b22', overlay: '#21262d',
    border: '#30363d', borderStrong: '#484f58',
    text: '#e6edf3', textSec: '#7d8590', textMuted: '#6e7681',
    accent: '#2f81f7', accentHover: '#58a6ff', success: '#3fb950', danger: '#f85149', warning: '#d29922'
  },
  {
    id: 'monokai-pro', name: 'Monokai Pro', base: 'dark',
    bg: '#2d2a2e', chrome: '#221f22', surface: '#2d2a2e', raised: '#363338', overlay: '#444145',
    border: '#403e41', borderStrong: '#524f52',
    text: '#fcfcfa', textSec: '#c1c0c0', textMuted: '#939293',
    accent: '#ffd866', accentHover: '#ffe28a', danger: '#ff6188', warning: '#fc9867'
  },
  {
    id: 'tokyo-night', name: 'Tokyo Night', base: 'dark',
    bg: '#1a1b26', chrome: '#16161e', surface: '#1a1b26', raised: '#24283b', overlay: '#2f3549',
    border: '#2f3549', borderStrong: '#3b4261',
    text: '#c0caf5', textSec: '#9aa5ce', textMuted: '#565f89',
    accent: '#7aa2f7', accentHover: '#95b4f9', success: '#9ece6a', danger: '#f7768e', warning: '#e0af68'
  },
  {
    id: 'catppuccin-mocha', name: 'Catppuccin Mocha', base: 'dark',
    bg: '#1e1e2e', chrome: '#181825', surface: '#1e1e2e', raised: '#28283d', overlay: '#313244',
    border: '#313244', borderStrong: '#45475a',
    text: '#cdd6f4', textSec: '#a6adc8', textMuted: '#7f849c',
    accent: '#89b4fa', accentHover: '#a0c4fb', success: '#a6e3a1', danger: '#f38ba8', warning: '#f9e2af'
  },
  {
    id: 'nord', name: 'Nord', base: 'dark',
    bg: '#2e3440', chrome: '#272b35', surface: '#2e3440', raised: '#3b4252', overlay: '#434c5e',
    border: '#434c5e', borderStrong: '#4c566a',
    text: '#eceff4', textSec: '#d8dee9', textMuted: '#7b8294',
    accent: '#88c0d0', accentHover: '#9fd0de', success: '#a3be8c', danger: '#bf616a', warning: '#ebcb8b'
  },
  {
    id: 'dracula', name: 'Dracula', base: 'dark',
    bg: '#282a36', chrome: '#21222c', surface: '#282a36', raised: '#343746', overlay: '#424458',
    border: '#44475a', borderStrong: '#565970',
    text: '#f8f8f2', textSec: '#b8bcca', textMuted: '#6272a4',
    accent: '#bd93f9', accentHover: '#caa5fb', success: '#50fa7b', danger: '#ff5555', warning: '#f1fa8c'
  },
  {
    id: 'solarized-dark', name: 'Solarized Dark', base: 'dark',
    bg: '#002b36', chrome: '#00252e', surface: '#073642', raised: '#0a4250', overlay: '#0f4d5c',
    border: '#0f4d5c', borderStrong: '#22606e',
    text: '#93a1a1', textSec: '#839496', textMuted: '#586e75',
    accent: '#268bd2', accentHover: '#3fa0e3', success: '#859900', danger: '#dc322f', warning: '#b58900'
  }
]

export const THEMES: ThemeDef[] = SPECS.map(expand)

export const THEME_MAP: Record<string, ThemeDef> = Object.fromEntries(
  THEMES.map((t) => [t.id, t])
)

export function getThemeDef(id: string): ThemeDef {
  return THEME_MAP[id] ?? THEMES[0]
}

export function applyTheme(id: string): void {
  const def = getThemeDef(id)
  const root = document.documentElement
  for (const [key, value] of Object.entries(def.vars)) {
    root.style.setProperty(key, value)
  }
  root.setAttribute('data-theme', def.base)
}

export function xtermThemeFor(id: string): XtermTheme {
  const def = getThemeDef(id)
  const v = def.vars
  const light = def.base === 'light'
  const accent = v['--color-accent']
  return {
    background: v['--color-bg'],
    foreground: v['--color-text'],
    cursor: accent,
    cursorAccent: v['--color-bg'],
    selectionBackground: light ? 'rgba(0,0,0,0.16)' : 'rgba(255,255,255,0.20)',
    black: light ? '#2a2a2a' : '#000000',
    red: v['--color-danger'],
    green: v['--color-success'],
    yellow: v['--color-warning'],
    blue: accent,
    magenta: light ? '#a347d1' : '#b06dff',
    cyan: light ? '#0a8aa0' : '#56b6c2',
    white: v['--color-text-secondary'],
    brightBlack: v['--color-text-muted'],
    brightRed: v['--color-danger'],
    brightGreen: v['--color-success'],
    brightYellow: v['--color-warning'],
    brightBlue: accent,
    brightMagenta: light ? '#a347d1' : '#b06dff',
    brightCyan: light ? '#0a8aa0' : '#56b6c2',
    brightWhite: v['--color-text']
  }
}
