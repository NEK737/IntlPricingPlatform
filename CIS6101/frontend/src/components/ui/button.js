import React from "react";

export function Button({ children, onClick, disabled, size = "md", className }) {
  const sizes = {
    sm: "px-2 py-1 text-sm",
    md: "px-3 py-2 text-base",
    lg: "px-4 py-3 text-lg"
  };
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 ${sizes[size]} ${className || ""}`}
    >
      {children}
    </button>
  );
}
