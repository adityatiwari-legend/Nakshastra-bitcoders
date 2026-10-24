import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'OrbisLuna — Lunar PSR Analysis & Exploration',
  description: 'Minimal scientific prototype for Lunar Permanently Shadowed Region detection, 3D lunar terrain, and rover route determination.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className="bg-[#07090e] text-slate-100 min-h-screen antialiased select-none" suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
