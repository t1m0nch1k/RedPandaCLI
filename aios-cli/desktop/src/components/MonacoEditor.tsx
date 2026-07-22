import { useRef, useCallback, useEffect, useState } from 'react'
import Editor, { OnMount } from '@monaco-editor/react'
import { setupMonaco, languageForFile } from '../lib/monacoSetup'

setupMonaco()

interface Props {
  path: string
  value: string
  onChange?: (value: string) => void
  readOnly?: boolean
  height?: string | number
}

export default function MonacoEditor({ path, value, onChange, readOnly, height }: Props) {
  const editorRef = useRef<Parameters<OnMount>[0] | null>(null)
  const [themeId, setThemeId] = useState('aios-dark')

  useEffect(() => {
    const obs = new MutationObserver(() => {
      const id = document.documentElement.getAttribute('data-theme-id') || 'aios-dark'
      setThemeId(id)
    })
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme', 'data-theme-id', 'style'] })
    return () => obs.disconnect()
  }, [])

  const handleMount: OnMount = useCallback((editor) => {
    editorRef.current = editor
    editor.focus()
  }, [])

  const handleChange = useCallback((val: string | undefined) => {
    onChange?.(val ?? '')
  }, [onChange])

  const language = languageForFile(path)

  return (
    <Editor
      height={height ?? '100%'}
      language={language}
      value={value}
      onChange={handleChange}
      onMount={handleMount}
      theme={themeId === 'aios-light' ? 'light' : 'aios-custom'}
      options={{
        fontFamily: "'JetBrains Mono', 'SF Mono', 'Cascadia Code', Consolas, 'Courier New', monospace",
        fontSize: 13,
        lineHeight: 20,
        minimap: { enabled: true },
        scrollBeyondLastLine: false,
        wordWrap: 'off',
        tabSize: 2,
        automaticLayout: true,
        readOnly: readOnly ?? false,
        cursorBlinking: 'smooth',
        cursorSmoothCaretAnimation: 'on',
        smoothScrolling: true,
        folding: true,
        foldingHighlight: true,
        lineNumbers: 'on',
        lineNumbersMinChars: 3,
        renderLineHighlight: 'line',
        renderWhitespace: 'selection',
        bracketPairColorization: { enabled: true },
        matchBrackets: 'always',
        autoClosingBrackets: 'always',
        autoClosingQuotes: 'always',
        formatOnPaste: true,
        suggestOnTriggerCharacters: true,
        quickSuggestions: true,
        multiCursorModifier: 'alt',
        copyWithSyntaxHighlighting: true,
        dragAndDrop: true,
        selectionHighlight: true,
        occurrencesHighlight: 'singleFile',
        renderControlCharacters: true,
        hideCursorInOverviewRuler: false,
        overviewRulerBorder: false,
        padding: { top: 8 },
      }}
    />
  )
}
