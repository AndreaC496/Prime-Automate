import type { Metadata } from 'next';
import { Barlow_Condensed, DM_Sans } from 'next/font/google';
import './globals.css';
import Navbar from '@/components/Navbar';

const barlow = Barlow_Condensed({
  subsets: ['latin'],
  weight: ['700', '800', '900'],
  variable: '--font-barlow',
});

const dmSans = DM_Sans({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  variable: '--font-dm',
});

export const metadata: Metadata = {
  title: 'Prime',
  description: 'AI-powered training card generator',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="it" className={`${barlow.variable} ${dmSans.variable}`}>
      <body>
        <main style={{ paddingBottom: '5rem' }}>{children}</main>
        <Navbar />
      </body>
    </html>
  );
}
