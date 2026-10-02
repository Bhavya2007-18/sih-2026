import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = { title: "PROJECT MAYA · Command Core", description: "Synthetic logistics simulation and planner decision support. No real-world execution." };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
