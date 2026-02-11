import asyncio
from daemon_heartbeat import HeartbeatDaemon

if __name__ == "__main__":
    try:
        asyncio.run(HeartbeatDaemon().pulse())
    except KeyboardInterrupt:
        print("Daemon gestopt.")
