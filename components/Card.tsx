import React from "react";
import { cn } from "@/lib/utils";

type Color = "pink" | "orange" | "lime" | "violet";
type Value =
  | "0"
  | "1"
  | "2"
  | "3"
  | "4"
  | "5"
  | "6"
  | "7"
  | "8"
  | "9"
  | "+2"
  | "+4"
  | "skip"
  | "reverse"
  | "wild";

interface CardProps {
  color?: Color;
  value: Value;
  className?: string;
}

const colorMap: Record<Color, string> = {
  pink: "from-pink-400 to-pink-600",
  orange: "from-orange-300 to-orange-500",
  lime: "from-lime-300  to-lime-500",
  violet: "from-violet-400 to-violet-600",
};

export default function Card({ color, value, className }: CardProps) {
  const neutral = value === "+4" || value === "wild";
  if (!neutral && !color) throw new Error("Color is required for this card value.");

  const bg = neutral ? "bg-[#1e3a8a]" : `bg-gradient-to-br ${colorMap[color!]}`;

  return (
    <div
      className={cn(
        "relative w-32 overflow-hidden h-52 rounded-[18px] border-[2px] border-black/30",
        bg,
        "shadow-[inset_0_0_0_4px_rgba(255,255,255,0.9)]",
        "shadow-lg",
        className
      )}
    >
      <span
        className={cn(
          "absolute inset-0 block origin-top-left rotate-12",
          neutral ? "bg-gradient-to-br from-white/10 via-white/5 to-transparent" : "bg-white/20",
          "mix-blend-overlay pointer-events-none"
        )}
      />

      <span className="absolute inset-x-0 top-0 h-1/3 rounded-t-[14px] bg-white/15 blur-[6px] pointer-events-none" />

      <Corner value={value} className="top-2 left-2" />
      <Corner value={value} className="bottom-2 right-2 rotate-180" />

      <span
        className={cn(
          "absolute inset-0 flex items-center justify-center text-white font-extrabold drop-shadow-md",
          value.length > 2 ? "text-3xl" : "text-6xl"
        )}
      >
        {iconify(value)}
      </span>
    </div>
  );
}

function Corner({ value, className }: { value: Value; className: string }) {
  return (
    <span className={cn("absolute text-white text-xs font-bold select-none", className)}>
      {iconify(value)}
    </span>
  );
}

function iconify(v: Value) {
  switch (v) {
    case "skip":
      return "⛔";
    case "reverse":
      return "🔄";
    case "wild":
      return "🎨";
    default:
      return v;
  }
}
