import { useState, useEffect } from 'react'
import { ChevronRight, File, Folder, FolderOpen } from 'lucide-react'
import { fileIcon, folderIcon, gitStatusIcon } from './iconMap'

export interface FileEntry {
  name: string
  path: string
  isDir: boolean
  size?: number
  modified?: number
  gitStatus?: string
}

interface Props {
  root: string
  entries: FileEntry[]
  expandedDirs: Set<string>
  onToggleDir: (path: string) => void
  onOpenFile: (path: string) => void
  onRefresh?: () => void
  onCreateFile?: (dir: string) => void
  onCreateDir?: (dir: string) => void
  onDelete?: (path: string) => void
  onRename?: (path: string) => void
  depth?: number
}

export default function FileTree({
  root: _root,
  entries,
  expandedDirs,
  onToggleDir,
  onOpenFile,
  depth = 0
}: Props) {
  const sorted = [...entries].sort((a, b) => {
    if (a.isDir !== b.isDir) return a.isDir ? -1 : 1
    return a.name.toLowerCase().localeCompare(b.name.toLowerCase())
  })

  return (
    <div className="file-tree" style={{ userSelect: 'none' }}>
      {sorted.map((entry) => (
        <FileTreeNode
          key={entry.path}
          entry={entry}
          expanded={expandedDirs.has(entry.path)}
          onToggle={() => onToggleDir(entry.path)}
          onOpen={() => onOpenFile(entry.path)}
          depth={depth}
        >
          {entry.isDir && expandedDirs.has(entry.path) && (
            <SubTree
              parentPath={entry.path}
              expandedDirs={expandedDirs}
              onToggleDir={onToggleDir}
              onOpenFile={onOpenFile}
              depth={depth + 1}
            />
          )}
        </FileTreeNode>
      ))}
    </div>
  )
}

function FileTreeNode({
  entry,
  expanded,
  onToggle,
  onOpen,
  depth,
  children,
}: {
  entry: FileEntry
  expanded: boolean
  onToggle: () => void
  onOpen: () => void
  depth: number
  children?: React.ReactNode
}) {
  const [hover, setHover] = useState(false)
  const icon = entry.isDir
    ? folderIcon(entry.name, expanded)
    : fileIcon(entry.name)

  return (
    <>
      <div
        className="file-tree-node"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 4,
          padding: '2px 8px 2px ' + (12 + depth * 16) + 'px',
          fontSize: 13,
          color: 'var(--color-text)',
          cursor: 'pointer',
          background: hover ? 'var(--color-surface-raised)' : 'transparent',
          borderRadius: 4,
          margin: '0 4px',
        }}
        onClick={entry.isDir ? onToggle : onOpen}
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => setHover(false)}
      >
        {entry.isDir ? (
          <ChevronRight
            size={10}
            style={{
              flexShrink: 0,
              transform: expanded ? 'rotate(90deg)' : 'none',
              transition: 'transform 0.1s',
              color: 'var(--color-text-muted)'
            }}
          />
        ) : (
          <span style={{ width: 10, flexShrink: 0 }} />
        )}
        {entry.isDir ? (
          expanded
            ? <FolderOpen size={14} style={{ flexShrink: 0, color: '#dcb67a' }} />
            : <Folder size={14} style={{ flexShrink: 0, color: '#b8944f' }} />
        ) : (
          <File size={14} style={{ flexShrink: 0, color: icon.color }} />
        )}
        <span style={{
          flex: 1,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap'
        }}>
          {entry.name}
        </span>
        {entry.gitStatus && (
          <span style={{
            fontSize: 10,
            fontWeight: 600,
            color: entry.gitStatus === 'M' ? 'var(--color-warning)'
              : entry.gitStatus === 'A' ? 'var(--color-success)'
              : entry.gitStatus === 'D' ? 'var(--color-danger)'
              : 'var(--color-text-muted)',
            flexShrink: 0,
          }}>
            {gitStatusIcon(entry.gitStatus)}
          </span>
        )}
      </div>
      {children}
    </>
  )
}

function SubTree({
  parentPath,
  expandedDirs,
  onToggleDir,
  onOpenFile,
  depth,
}: {
  parentPath: string
  expandedDirs: Set<string>
  onToggleDir: (path: string) => void
  onOpenFile: (path: string) => void
  depth: number
}) {
  const [children, setChildren] = useState<FileEntry[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    loadDir(parentPath).then((entries) => {
      if (!cancelled) {
        setChildren(entries)
        setLoading(false)
      }
    }).catch(() => {
      if (!cancelled) setLoading(false)
    })
    return () => { cancelled = true }
  }, [parentPath])

  if (loading) {
    return (
      <div style={{ paddingLeft: 28 + depth * 16, color: 'var(--color-text-muted)', fontSize: 11 }}>
        Loading...
      </div>
    )
  }

  const sorted = [...children].sort((a, b) => {
    if (a.isDir !== b.isDir) return a.isDir ? -1 : 1
    return a.name.toLowerCase().localeCompare(b.name.toLowerCase())
  })

  return (
    <>
      {sorted.map((entry) => (
        <FileTreeNode
          key={entry.path}
          entry={entry}
          expanded={expandedDirs.has(entry.path)}
          onToggle={() => onToggleDir(entry.path)}
          onOpen={() => onOpenFile(entry.path)}
          depth={depth}
        >
          {entry.isDir && expandedDirs.has(entry.path) && (
            <SubTree
              parentPath={entry.path}
              expandedDirs={expandedDirs}
              onToggleDir={onToggleDir}
              onOpenFile={onOpenFile}
              depth={depth + 1}
            />
          )}
        </FileTreeNode>
      ))}
    </>
  )
}

async function loadDir(path: string): Promise<FileEntry[]> {
  try {
    const { invoke } = await import('@tauri-apps/api/core')
    const result = await invoke<{ entries: { name: string; is_dir: boolean; size: number; modified: number }[] }>('fs_list', { path })
    return result.entries.map((e) => ({
      name: e.name,
      path: path + '/' + e.name,
      isDir: e.is_dir,
      size: e.size,
      modified: e.modified,
    }))
  } catch {
    return []
  }
}
