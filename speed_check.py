import argparse
import ssl
import sys
import time
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

import certifi


REQUEST_COUNT = 10


def download_file(url: str, context: ssl.SSLContext) -> tuple[int, float]:
    request = Request(
        url,
        headers={
            "Cache-Control": "no-cache",
            "User-Agent": "internet-speed-check/1.0 (https://github.com/Damoclezzz/internet-speed-check)",
        },
    )
    downloaded_bytes = 0
    started_at = time.perf_counter()

    with urlopen(request, timeout=30, context=context) as response:
        while chunk := response.read(64 * 1024):
            downloaded_bytes += len(chunk)

    return downloaded_bytes, time.perf_counter() - started_at


def calculate_speed_mbps(downloaded_bytes: int, elapsed_seconds: float) -> float:
    return downloaded_bytes * 8 / elapsed_seconds / 1_000_000


def main() -> int:
    parser = argparse.ArgumentParser(description="Замер скорости скачивания за 10 запросов")
    parser.add_argument("url", help="прямая ссылка на файл (HTTP или HTTPS)")
    args = parser.parse_args()

    if urlsplit(args.url).scheme not in ("http", "https"):
        parser.error("укажите полный HTTP или HTTPS URL")

    context = ssl.create_default_context(cafile=certifi.where())
    total_bytes = 0
    total_seconds = 0.0

    for number in range(1, REQUEST_COUNT + 1):
        try:
            downloaded_bytes, elapsed_seconds = download_file(args.url, context)
        except (URLError, OSError, ValueError) as error:
            print(f"Ошибка при запросе {number}/{REQUEST_COUNT}: {error}", file=sys.stderr)

            return 1

        total_bytes += downloaded_bytes
        total_seconds += elapsed_seconds
        print(f"Запрос {number}/{REQUEST_COUNT}: {downloaded_bytes} байт за {elapsed_seconds:.3f} с")

    print(f"Среднее время запроса: {total_seconds / REQUEST_COUNT:.3f} с")
    print(f"Всего скачано: {total_bytes} байт")
    print(f"Скорость скачивания: {calculate_speed_mbps(total_bytes, total_seconds):.2f} Мбит/с")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
