import React from "react";

export function Badge({ children }) {
  return (
    <span className="inline-block px-2 py-1 text-xs rounded bg-gray-200 text-gray-700">
      {children}
    </span>
  );
}
