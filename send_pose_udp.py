import argparse
import json
import socket
import time

pose_path = r"C:\Users\jacks\AppData\Roaming\PrismLauncher\instances\1.21.11\minecraft\minescript\player_pose.txt"

def read_pose(path):
    with open(path, "r", encoding="utf-8") as handle:
        content = handle.read().strip()
    if not content:
        raise ValueError("pose file is empty")

    parts = [p.strip() for p in content.split(",")]
    if len(parts) < 3:
        raise ValueError("pose file must contain x,y,theta")

    x = float(parts[0])
    y = float(parts[1])
    theta = float(parts[2])
    return x, y, theta


def send_pose(host, port, x, y, theta):
    payload = {"x": x, "z": y, "theta": theta}
    message = json.dumps(payload).encode("utf-8")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.sendto(message, (host, port))
    finally:
        sock.close()


def main():
    parser = argparse.ArgumentParser(description="Send pose over UDP from a txt file.")
    parser.add_argument("--file", default=pose_path, help="Path to pose txt file")
    parser.add_argument("--host", default="192.168.0.251", help="UDP host")
    parser.add_argument("--port", type=int, default=5005, help="UDP port")
    parser.add_argument("--interval", type=float, default=0.1, help="Send interval in seconds")
    args = parser.parse_args()

    try:
        while True:
            x, y, theta = read_pose(args.file)
            send_pose(args.host, args.port, x, y, theta)
            print(f"Sent pose to {args.host}:{args.port} -> x={x}, y={y}, theta={theta}")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
