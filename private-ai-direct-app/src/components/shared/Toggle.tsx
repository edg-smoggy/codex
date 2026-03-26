interface ToggleProps {
  checked: boolean;
  onChange: () => void;
  label?: string;
}

export function Toggle({ checked, onChange, label }: ToggleProps) {
  return (
    <button
      type="button"
      className={checked ? "toggle on" : "toggle"}
      onClick={onChange}
      aria-pressed={checked}
      aria-label={label || "toggle"}
    />
  );
}
