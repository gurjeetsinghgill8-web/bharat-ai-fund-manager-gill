// src/components/ClearableInput.jsx — a search box you can actually clear.
//
// Why this exists: every filter box on these pages used to be a bare <input> with no way back.
// After typing a symbol you had to select the text and delete it by hand before searching for
// the next stock — the fund manager's complaint was "you have to delete all the things".
// This wraps the same .input styling with a one-click ✕ and, when there are no matches, an
// inline hint so an empty table is never a mystery.
import { useEffect, useRef } from 'react';

export default function ClearableInput({
  value,
  onChange,
  placeholder,
  label,
  matchCount,
  totalCount,
  style,
  type = 'text',
}) {
  const ref = useRef(null);

  // ESC clears the box — the keyboard version of the ✕ button.
  useEffect(() => {
    function onKey(e) {
      if (e.key === 'Escape' && document.activeElement === ref.current) {
        onChange('');
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onChange]);

  const hasText = value !== '' && value !== null && value !== undefined;
  const noMatch = hasText && typeof matchCount === 'number' && matchCount === 0;

  return (
    <div style={{ position: 'relative', ...style }}>
      {label && <div className="input-label">{label}</div>}
      <input
        ref={ref}
        className="input"
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        autoComplete="off"
        spellCheck={false}
        style={{ paddingRight: hasText ? 30 : undefined }}
      />
      {hasText && (
        <button
          type="button"
          onClick={() => { onChange(''); ref.current?.focus(); }}
          title="Clear (Esc)"
          aria-label="Clear search"
          style={{
            position: 'absolute',
            right: 8,
            bottom: 8,
            width: 20,
            height: 20,
            lineHeight: '18px',
            padding: 0,
            border: 'none',
            borderRadius: '50%',
            background: 'var(--bg-card-hover, rgba(255,255,255,0.12))',
            color: 'var(--text-secondary, #9aa4b2)',
            cursor: 'pointer',
            fontSize: 12,
            fontWeight: 700,
          }}
        >
          ✕
        </button>
      )}
      {noMatch && (
        <div style={{ fontSize: 10.5, color: 'var(--orange, #FF9F43)', marginTop: 3 }}>
          No match in {totalCount} rows — press ✕ or Esc to clear
        </div>
      )}
    </div>
  );
}
