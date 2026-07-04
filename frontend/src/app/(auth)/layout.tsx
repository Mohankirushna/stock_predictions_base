export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-1 items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-lg font-semibold tracking-tight">AI Investment Research</h1>
          <p className="mt-1 text-sm text-muted">Research-first. Never a trade order.</p>
        </div>
        {children}
      </div>
    </div>
  );
}
