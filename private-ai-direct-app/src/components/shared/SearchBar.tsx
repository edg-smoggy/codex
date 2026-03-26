interface SearchBarProps {
  value: string;
  placeholder?: string;
  inputId?: string;
  onChange: (value: string) => void;
}

export function SearchBar({ value, placeholder = "搜索", inputId, onChange }: SearchBarProps) {
  return (
    <label className="search-box sidebar-search" aria-label="搜索对话">
      <span className="search-icon">🔍</span>
      <input
        id={inputId}
        type="search"
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
      />
      {value ? (
        <button className="search-clear" type="button" onClick={() => onChange("")} aria-label="清空搜索">
          ✕
        </button>
      ) : null}
    </label>
  );
}
