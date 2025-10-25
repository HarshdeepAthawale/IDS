import Layout from "@/components/layout"
import RealtimeDashboard from "@/components/realtime-dashboard"

export default function RealtimePage() {
  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Real-time Dashboard</h1>
          <p className="text-muted-foreground mt-2">Live monitoring of network traffic and security events</p>
        </div>
        <RealtimeDashboard />
      </div>
    </Layout>
  )
}
