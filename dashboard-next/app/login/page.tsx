import { redirect } from 'next/navigation'

// Legacy /login URL — redirect to Clerk sign-in
export default function LoginPage() {
  redirect('/sign-in')
}
