import './globals.css';

export const metadata = {
  title: 'StandScout | Expo Visit Planner',
  description: 'Prioritise the best exhibitor stands to visit at Hardware Pioneers MAX 26.'
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
