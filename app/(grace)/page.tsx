// AI_HEADER
// module: M-WEB-HOME-REDIRECT
// wave: W-2.2
// purpose: Redirect home to /day/today

import { redirect } from 'next/navigation';

export default function HomePage() {
  redirect('/day/today');
}
