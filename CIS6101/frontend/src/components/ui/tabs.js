import React from "react";

// Dummy Tabs wrapper
export function Tabs({ children }) {
  return <div className="tabs">{children}</div>;
}

// Dummy TabsList
export function TabsList({ children }) {
  return <div className="tabs-list">{children}</div>;
}

// Dummy TabsTrigger
export function TabsTrigger({ children, onClick }) {
  return (
    <button className="tabs-trigger" onClick={onClick}>
      {children}
    </button>
  );
}

// Dummy TabsContent
export function TabsContent({ children }) {
  return <div className="tabs-content">{children}</div>;
}
