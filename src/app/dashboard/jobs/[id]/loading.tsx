import { Card, CardContent, CardHeader } from "@/components/ui/card";

export default function Loading() {
  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <Card>
        <CardHeader>
          <div className="h-8 w-3/4 bg-gray-200 rounded animate-pulse" />
          <div className="space-y-2 mt-2">
            <div className="h-4 w-1/2 bg-gray-200 rounded animate-pulse" />
            <div className="h-4 w-1/3 bg-gray-200 rounded animate-pulse" />
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="h-4 w-1/4 bg-gray-200 rounded animate-pulse" />
            <div className="space-y-2">
              <div className="h-4 w-full bg-gray-200 rounded animate-pulse" />
              <div className="h-4 w-full bg-gray-200 rounded animate-pulse" />
              <div className="h-4 w-3/4 bg-gray-200 rounded animate-pulse" />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="h-6 w-1/2 bg-gray-200 rounded animate-pulse" />
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="h-32 bg-gray-200 rounded animate-pulse" />
            <div className="h-32 bg-gray-200 rounded animate-pulse" />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="h-6 w-1/2 bg-gray-200 rounded animate-pulse" />
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            <div className="space-y-2">
              <div className="h-4 w-1/4 bg-gray-200 rounded animate-pulse" />
              <div className="flex flex-wrap gap-2">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="h-6 w-20 bg-gray-200 rounded animate-pulse" />
                ))}
              </div>
            </div>

            <div className="space-y-4">
              {[1, 2].map((i) => (
                <div key={i} className="space-y-2">
                  <div className="h-4 w-1/3 bg-gray-200 rounded animate-pulse" />
                  <div className="h-4 w-1/4 bg-gray-200 rounded animate-pulse" />
                  <div className="h-4 w-1/5 bg-gray-200 rounded animate-pulse" />
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
} 