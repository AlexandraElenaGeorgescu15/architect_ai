import { Wifi, WifiOff } from 'lucide-react'
import { useWebSocketStatus } from '../../hooks/useWebSocket'

export default function ConnectionStatus() {
  const { isConnected } = useWebSocketStatus()

  return (
    <div className="flex items-center gap-2">
      {isConnected ? (
        <Wifi className="w-4 h-4 text-green-500" title="Connected" />
      ) : (
        <WifiOff className="w-4 h-4 text-red-500" title="Disconnected" />
      )}
    </div>
  )
}

