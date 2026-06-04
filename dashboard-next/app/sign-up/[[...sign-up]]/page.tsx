import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <div className="flex min-h-[100dvh] items-center justify-center px-4 py-8">
      <SignUp />
    </div>
  );
}
