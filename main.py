#!/usr/bin/env python3
from typing import Any, Generator
import requests, getpass, threading, json, yt_dlp
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup


def get_id(viewerUrl: str):
    return (
        id[0]
        if ((id := parse_qs(urlparse(viewerUrl).query).get("id")) != None)
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

    for i, viewerUrl in enumerate(viewerUrl_list):
        folderName = folderName.replace("\\/", " ")
        threading.Thread(
            target=download,
            args=[
                s,
                get_id(viewerUrl),
                f"{folderName}/{i}.mp4",
            ],
        ).start()


def main():
    email = input("email: ").strip()
    password = getpass.getpass("password ('*' not shown): ").strip()

    s = next(get_session_with_cookies(email, password))

    url = input("url: ").strip()

    if id := get_id(url):
        download(s, id)
    elif folderID := parse_qs(urlparse(url).fragment).get("folderID"):
        download_folder(s, folderID[0].strip('"'))
    else:
        exit("NOT SUPPORTED\n")


main()
