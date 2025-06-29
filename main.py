#!/usr/bin/env python3
import getpass
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Generator
from urllib.parse import parse_qs, urlparse

import requests
import yt_dlp
from bs4 import BeautifulSoup
from dotenv import load_dotenv


def get_id(viewerUrl: str):
    return (
        id[0]
        if ((id := parse_qs(urlparse(viewerUrl).query).get("id")) is not None)
        else None
    )


def get_session_with_cookies(
    email: str, password: str
) -> Generator[requests.Session, None, None]:
    with requests.Session() as s:
        s.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            }
        )

        action = f'https://idp.unibo.it{str(BeautifulSoup(s.get("https://virtuale.unibo.it/login/index.php").text, features="html.parser").select_one("#hrd")["action"])}'
        body = {
            "HomeRealmSelection": "AD AUTHORITY",
            "Email": "",
        }

        r = s.post(action, allow_redirects=True, data=body)

        body = {
            "UserName": email,
            "Password": password,
            "AuthMethod": "FormsAuthentication",
        }
        soup = BeautifulSoup(s.post(r.url, data=body).text, features="html.parser")
        action = str(soup.select_one('form[name="hiddenform"]')["action"])
        SAMLResponse = str(soup.select_one('input[name="SAMLResponse"]')["value"])
        RelayState = str(soup.select_one('input[name="RelayState"]')["value"])

        body = {
            "SAMLResponse": f"{SAMLResponse}",
            "RelayState": f"{RelayState}",
        }
        s.post(url=action, allow_redirects=True, data=body)
        s.get(
            "https://unibo.cloud.panopto.eu/Panopto/Pages/Auth/Login.aspx?instance=Virtuale&AllowBounce=true",
            allow_redirects=True,
        )

        yield s


def download(s: requests.Session, id: str, path: str | None = None):
    s.get(f"https://unibo.cloud.panopto.eu/Panopto/Pages/Viewer.aspx?id={id}")

    with open("payload2.json") as f:
        payload: dict[str, Any] = json.load(f)
    payload["deliveryId"] = id

    delivery_json = s.post(
        "https://unibo.cloud.panopto.eu/Panopto/Pages/Viewer/DeliveryInfo.aspx",
        data=payload,
    ).json()["Delivery"]
    streamUrl = delivery_json["PodcastStreams"][0]["StreamUrl"]
    sessionGroupLongName = delivery_json["SessionGroupLongName"]
    sessionName = delivery_json["SessionName"]

    with yt_dlp.YoutubeDL(
        {
            "quiet": True,
            "outtmpl": (
                path
                if path
                else f"{sessionGroupLongName} {sessionName}.mp4".replace(
                    "/", "-"
                )  # TODO add year
            ),
        }
    ) as ydl:
        ydl.download(streamUrl)


def download_folder(s: requests.Session, folderID: str):

    s.get(
        f'https://unibo.cloud.panopto.eu/Panopto/Pages/Sessions/List.aspx#folderID="{folderID}"&page=0&maxResults=250'
    )

    with open("payload.json") as f:
        payload: dict[str, dict[str, Any]] = json.load(f)
    payload["queryParameters"]["folderID"] = folderID

    results_json = s.post(
        "https://unibo.cloud.panopto.eu/Panopto/Services/Data.svc/GetSessions",
        json=payload,
    ).json()["d"]["Results"]

    viewerUrl_list: list[str] = [res["ViewerUrl"] for res in results_json]

    folderName: str = results_json[0]["FolderName"]
    folderName = folderName.replace("\\/", " ")

    print(f"Found {len(viewerUrl_list)} videos in folder '{folderName}'")

    # Download videos sequentially within the folder to avoid overwhelming the server
    for i, viewerUrl in enumerate(viewerUrl_list):
        print(
            f"Downloading video {i+1}/{len(viewerUrl_list)} from folder '{folderName}'"
        )
        download(s, get_id(viewerUrl), f"{folderName}/{i+1:03d}.mp4")


def read_urls_from_file(file_path: str) -> list[str]:
    """Read URLs from a text file, one URL per line. Ignore empty lines and comments."""
    urls = []
    try:
        with open(file_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    urls.append(line)
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file '{file_path}': {e}")
        sys.exit(1)
    return urls


def process_single_url(
    s: requests.Session, url: str, url_index: int, total_urls: int
) -> tuple[str, bool, str]:
    """Process a single URL and return result info."""
    print(f"Processing URL {url_index}/{total_urls}: {url}")
    try:
        if id := get_id(url):
            download(s, id)
            return url, True, "Downloaded successfully"
        elif folderID := parse_qs(urlparse(url).fragment).get("folderID"):
            download_folder(s, folderID[0].strip('"'))
            return url, True, "Folder downloaded successfully"
        else:
            return url, False, "URL not supported"
    except Exception as e:
        return url, False, f"Error: {e}"


def get_credentials() -> tuple[str, str]:
    """Get credentials from environment variables or prompt user."""
    email = os.getenv("PANOPTO_EMAIL")
    password = os.getenv("PANOPTO_PASSWORD")

    if not email:
        email = input("email: ").strip()
    else:
        print(f"Using email from environment: {email}")

    if not password:
        password = getpass.getpass("password ('*' not shown): ").strip()
    else:
        print("Using password from environment variable.")

    return email, password


def main():
    # Load environment variables from .env file
    load_dotenv()

    # Check if a URLs file is provided as command line argument
    if len(sys.argv) > 1:
        urls_file = sys.argv[1]
        urls = read_urls_from_file(urls_file)
        print(f"Found {len(urls)} URLs in '{urls_file}'")
    else:
        urls = []

    # Get number of parallel downloads from environment or use default
    max_workers = int(os.getenv("MAX_PARALLEL_DOWNLOADS", "3"))
    print(f"Using {max_workers} parallel downloads")

    # Get credentials from environment or prompt
    email, password = get_credentials()

    s = next(get_session_with_cookies(email, password))

    # If URLs file was provided, process all URLs
    if urls:
        print("Processing URLs from file...")

        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_url = {
                executor.submit(process_single_url, s, url, i + 1, len(urls)): url
                for i, url in enumerate(urls)
            }

            # Process completed tasks
            completed = 0
            for future in as_completed(future_to_url):
                url, success, message = future.result()
                completed += 1
                status = "✓" if success else "✗"
                print(f"[{completed}/{len(urls)}] {status} {url}: {message}")
    else:
        # Original behavior: prompt for single URL
        url = input("url: ").strip()

        if id := get_id(url):
            download(s, id)
        elif folderID := parse_qs(urlparse(url).fragment).get("folderID"):
            download_folder(s, folderID[0].strip('"'))
        else:
            exit("NOT SUPPORTED\n")


main()
