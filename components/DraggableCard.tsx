"use client";
import { motion } from "framer-motion";
import { ReactNode } from "react";

interface DraggableCardProps {
  children: ReactNode;
}

export default function DraggableCard({ children }: DraggableCardProps) {
  return (
    <motion.div
      drag
      dragSnapToOrigin
      dragElastic={0.2} // наскільки "пружно" тягнеться
      whileDrag={{ scale: 1.1, rotate: 5 }} // невелика анімація під час drag
      transition={{
        type: "spring",
        stiffness: 300,
        damping: 20,
      }}
      className="cursor-grab active:cursor-grabbing"
    >
      {children}
    </motion.div>
  );
}
