export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-slate-900">
      <div className="max-w-7xl mx-auto py-12 sm:px-6 lg:px-8">
        {children}
      </div>
    </div>
  );
} 