import React from "react";

export function Input({ value, onChange, onKeyDown, placeholder }) {
  return (
    <input
      className="w-full border rounded px-3 py-2"
      value={value}
      onChange={onChange}
      onKeyDown={onKeyDown}
      placeholder={placeholder}
    />
  );
}
