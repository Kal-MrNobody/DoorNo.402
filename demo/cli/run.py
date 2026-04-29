import sys
import os
import time

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), "..", "..", "sdk", "python"
))

import httpx
import pyfiglet
from dotenv import load_dotenv
from eth_account import Account
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from web3 import Web3

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

console = Console()

AGENT_ADDRESS = os.environ.get("AGENT_ADDRESS", "")
PRIVATE_KEY = os.environ.get("AGENT_PRIVATE_KEY", "")
BLOG_URL = os.environ.get("BLOG_URL", "http://localhost:3000")
USDC_CONTRACT = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
RPC_URL = "https://sepolia.base.org"

w3 = Web3(Web3.HTTPProvider(RPC_URL))

USDC_ABI = [
    {"name": "balanceOf", "type": "function",
     "inputs": [{"name": "a", "type": "address"}],
     "outputs": [{"type": "uint256"}], "stateMutability": "view"},
    {"name": "transfer", "type": "function",
     "inputs": [{"name": "to", "type": "address"},
                {"name": "amount", "type": "uint256"}],
     "outputs": [{"type": "bool"}], "stateMutability": "nonpayable"},
]
usdc = w3.eth.contract(
    address=Web3.to_checksum_address(USDC_CONTRACT), abi=USDC_ABI
)


def get_balance():
    raw = usdc.functions.balanceOf(
        Web3.to_checksum_address(AGENT_ADDRESS)
    ).call()
    return raw / 1_000_000


def check_env():
    missing = []
    if not AGENT_ADDRESS:
        missing.append("AGENT_ADDRESS")
    if not PRIVATE_KEY:
        missing.append("AGENT_PRIVATE_KEY")
    if missing:
        console.print(Panel(
            f"Missing .env keys: {', '.join(missing)}",
            style="bold red"
        ))
        sys.exit(1)


def step(msg, style="bright_yellow", prefix=">"):
    console.print(f"  [bold {style}]{prefix}[/bold {style}] [white]{msg}[/white]")


def show_header():
    os.system("cls" if os.name == "nt" else "clear")
    
    # Retro ASCII Art Header
    ascii_art = pyfiglet.figlet_format("DOORNO.402", font="block")
    console.print(f"[bold magenta]{ascii_art}[/bold magenta]", end="")
    
    console.print("[bold cyan]  x402 Payment Security SDK Demo Environment[/bold cyan]")
    console.print("  [dim]────────────────────────────────────────────────────────────────────────[/dim]")
    
    balance = get_balance()
    short_addr = AGENT_ADDRESS[:6] + "..." + AGENT_ADDRESS[-4:]
    
    console.print(f"  [dim white]Wallet connected:[/dim white] [bold bright_yellow]{short_addr}[/bold bright_yellow]")
    console.print(f"  [dim white]Session balance:[/dim white]  [bold bright_green]{balance:.2f} USDC[/bold bright_green]")
    console.print("  [dim]────────────────────────────────────────────────────────────────────────[/dim]\n")


def show_balance(before, after, mode="unprotected"):
    console.print()
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="dim white")
    table.add_column(style="bold cyan")
    table.add_row("Before Attack", f"{before:.2f} USDC")
    table.add_row("After Attack", f"{after:.2f} USDC")
    diff = before - after
    if mode == "unprotected":
        table.add_row("Total Drained", f"[bold bright_red]-${diff:.2f}[/bold bright_red]")
    else:
        table.add_row("Total Saved", f"[bold bright_green]+${diff:.2f}[/bold bright_green]")
    
    color = "bright_red" if mode == "unprotected" else "bright_green"
    console.print(Panel(table, title=f"[bold {color}]Wallet Status[/bold {color}]", style=color, expand=False))


def show_payment_table(described, demanded, inflation):
    console.print()
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="dim white", width=20)
    table.add_column(style="bold white")
    table.add_row("Description says", f"[bold bright_green]${described:.2f}[/bold bright_green]")
    table.add_row("Protocol demands", f"[bold bright_red]${demanded:.2f}[/bold bright_red]")
    table.add_row("Inflation Rate", f"[bold bright_red]{inflation:,.0f}%[/bold bright_red]")
    table.add_row("Security Threshold", "5%")
    console.print(Panel(
        table,
        title="[bold magenta]x402 Payment Intercepted[/bold magenta]",
        style="magenta",
        expand=False
    ))


def main_menu():
    while True:
        show_header()
        console.print("  [bold cyan]Select an environment to simulate:[/bold cyan]")
        console.print("  [bold magenta]1.[/bold magenta] [bold white]Standard AI Agent[/bold white]         [dim](Vulnerable, no SDK installed)[/dim]")
        console.print("  [bold magenta]2.[/bold magenta] [bold white]Secure Agent[/bold white]              [dim](Powered by DoorNo.402 SDK)[/dim]")
        console.print("  [bold magenta]3.[/bold magenta] [bold white]Live Attack Comparison[/bold white]    [dim](Run both side-by-side)[/dim]")
        console.print("  [bold magenta]4.[/bold magenta] [bold white]Wild URL Testing[/bold white]          [dim](Test custom URLs with SDK)[/dim]")
        console.print("  [bold magenta]5.[/bold magenta] [bold white]Find x402 Sites[/bold white]           [dim](Search the web for real endpoints)[/dim]")
        console.print("  [dim]q. Shutdown system[/dim]")
        console.print()
        
        choice = console.input("  [bold magenta]>[/bold magenta] ").strip().lower()
        url = f"{BLOG_URL}/api/articles/bitcoin-etf-analysis"
        
        if choice == "1":
            run_unprotected(url)
            pause()
        elif choice == "2":
            run_protected(url)
            pause()
        elif choice == "3":
            run_side_by_side(url)
            pause()
        elif choice == "4":
            run_custom()
            pause()
        elif choice == "5":
            run_search()
            pause()
        elif choice == "q":
            console.print("\n  [dim]Shutting down environment...[/dim]")
            break
        else:
            console.print("  [bold red]Invalid selection.[/bold red]")
            time.sleep(1)


def pause():
    console.print()
    console.input("  [dim]Press Enter to return to menu...[/dim]")


def fetch_402(url):
    try:
        resp = httpx.get(url, timeout=10)
    except (httpx.ConnectError, httpx.ConnectTimeout,
            httpx.ReadTimeout, httpx.HTTPError, Exception):
        return None, "server_down"
    if resp.status_code != 402:
        return resp, "not_402"
    data = resp.json()
    req = data["accepts"][0]
    return {
        "pay_to": req["payTo"],
        "raw_amount": int(req["maxAmountRequired"]),
        "demanded": int(req["maxAmountRequired"]) / 1_000_000,
        "description": req["description"],
        "data": data,
    }, "402"


def run_unprotected(url):
    console.print()
    step("Initializing standard agent...")
    time.sleep(0.6)
    step(f"Requesting resource: [cyan]{url}[/cyan]")
    time.sleep(0.4)

    result, status = fetch_402(url)
    if status == "server_down":
        console.print(Panel(
            "Target server unreachable.\n"
            "Ensure blog backend is running: cd demo/blog/backend && node server.js",
            style="bold bright_red",
            expand=False
        ))
        return
    if status == "not_402":
        step(f"Server responded: HTTP {result.status_code} (no paywall)", "dim white", "*")
        return

    step("Server responded: HTTP 402 Payment Required", "bright_red", "!")
    time.sleep(0.3)

    from doorno402.validators.price import extract_price
    described = extract_price(result["description"]) or 0.0
    demanded = result["demanded"]
    inflation = ((demanded - described) / described * 100) if described else 0

    show_payment_table(described, demanded, inflation)
    time.sleep(0.5)
    
    console.print()
    step("Agent parsing description...", "bright_cyan")
    step(f"Agent identified price: ${described:.2f}", "bright_cyan")
    step("Agent executing protocol payment...", "bright_cyan")
    time.sleep(0.8)

    step("Signing Ethereum transaction...", "bright_yellow")
    time.sleep(0.8)

    account = Account.from_key(PRIVATE_KEY)
    tx = usdc.functions.transfer(
        Web3.to_checksum_address(result["pay_to"]), result["raw_amount"]
    ).build_transaction({
        "from": Web3.to_checksum_address(AGENT_ADDRESS),
        "nonce": w3.eth.get_transaction_count(
            Web3.to_checksum_address(AGENT_ADDRESS)),
        "gas": 100000,
        "gasPrice": w3.eth.gas_price,
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

    step("Transaction confirmed on Base Sepolia", "bright_green" if receipt.status else "bright_red", "✓")
    console.print(f"    [dim cyan]Tx Hash: {tx_hash.hex()}[/dim cyan]")
    link = f"https://sepolia.basescan.org/tx/{tx_hash.hex()}"
    console.print(f"    [dim white]View on Explorer: [underline]{link}[/underline][/dim white]")
    time.sleep(0.3)

    after = get_balance()
    before = after + demanded
    show_balance(before, after, "unprotected")
    console.print(Panel(
        "CRITICAL FAILURE: Agent fell victim to x402 price inflation exploit.",
        style="bold bright_red",
        expand=False
    ))


def run_protected(url):
    console.print()
    step("Initializing secure agent [DoorNo.402 SDK loaded]...")
    time.sleep(0.6)
    step(f"Requesting resource: [cyan]{url}[/cyan]")
    time.sleep(0.4)

    result, status = fetch_402(url)
    if status == "server_down":
        console.print(Panel(
            "Target server unreachable.\n"
            "Ensure blog backend is running: cd demo/blog/backend && node server.js",
            style="bold bright_red",
            expand=False
        ))
        return
    if status == "not_402":
        step(f"Server responded: HTTP {result.status_code} (no paywall)", "dim white", "*")
        return

    step("Server responded: HTTP 402 Payment Required", "bright_red", "!")
    time.sleep(0.3)

    from doorno402.validators.price import extract_price, validate_price
    described = extract_price(result["description"]) or 0.0
    demanded = result["demanded"]
    inflation = ((demanded - described) / described * 100) if described else 0

    show_payment_table(described, demanded, inflation)
    time.sleep(0.5)

    console.print()
    step("DoorNo.402 intercepting protocol execution...", "bright_magenta", "⚡")
    time.sleep(0.8)

    validation = validate_price(result["data"])

    if not validation["valid"]:
        console.print("  " + Panel(
            validation["reason"],
            style="bold bright_red",
            expand=False
        ))
        time.sleep(0.3)

        before = get_balance()
        show_balance(before, before, "protected")
        console.print(Panel(
            "THREAT NEUTRALIZED: DoorNo.402 successfully blocked fraudulent transaction.",
            style="bold bright_green",
            expand=False
        ))

        console.print()
        step("Appending forensic data to blocked_payments.log...", "dim white", "»")
        ts = time.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        log_line = (
            f"{ts} | {url} | described=${described:.2f} | "
            f"demanded=${demanded:.2f} | inflation={inflation:.0f}%\n"
        )
        with open("blocked_payments.log", "a") as f:
            f.write(log_line)
        time.sleep(0.3)

        try:
            with open("blocked_payments.log") as f:
                lines = f.readlines()
                last = lines[-1].strip() if lines else ""
            console.print("  " + Panel(last, style="dim white", expand=False))
        except FileNotFoundError:
            pass
    else:
        step("Payment approved by DoorNo.402 -- price is legitimate", "bright_green", "✓")


def run_side_by_side(url):
    console.print()
    console.print("  [bold bright_red]========================================================================[/bold bright_red]")
    console.print("  [bold bright_red]                      WITHOUT DOORNO.402 SDK                            [/bold bright_red]")
    console.print("  [bold bright_red]========================================================================[/bold bright_red]")
    run_unprotected(url)
    console.print()
    console.print()
    console.print("  [bold bright_green]========================================================================[/bold bright_green]")
    console.print("  [bold bright_green]                        WITH DOORNO.402 SDK                             [/bold bright_green]")
    console.print("  [bold bright_green]========================================================================[/bold bright_green]")
    run_protected(url)


def run_custom():
    console.print()
    url = console.input("  [bold cyan]Enter URL to fetch:[/bold cyan] ").strip()
    if not url:
        return
        
    console.print()
    step(f"Testing wild URL: [cyan]{url}[/cyan]")
    time.sleep(0.4)

    result, status = fetch_402(url)
    if status == "server_down":
        console.print(Panel("Connection failed. Server might be down or invalid.", style="bold bright_red", expand=False))
        return

    if status == "not_402":
        code = result.status_code
        step(f"Server responded: HTTP {code}", "dim white", "*")
        if code == 200:
            body = result.text[:500]
            console.print(Panel(body, title="[bold cyan]Response Preview[/bold cyan]", style="dim white", expand=False))
        else:
            console.print(Panel(f"HTTP {code}", style="bright_yellow", expand=False))
        return

    step("HTTP 402 Payment Required detected!", "bold bright_green", "✓")
    time.sleep(0.3)
    
    # Force the secure agent flow for wild URLs to show off the SDK
    run_protected(url)


def run_search():
    console.print()
    step("Scanning the internet for x402-enabled endpoints...", "bright_magenta", "⚡")

    try:
        from duckduckgo_search import DDGS
    except ImportError:
        console.print(Panel(
            "duckduckgo-search not installed.\n"
            "pip install duckduckgo-search",
            style="bold bright_red",
            expand=False
        ))
        return

    skip = ["github.com", "docs.", "medium.com", "blog.", "arxiv.org"]
    urls = []

    try:
        with DDGS() as ddgs:
            queries = [
                "x402 payment protocol site",
                "x402 HTTP payment AI agent",
            ]
            for q in queries:
                for r in ddgs.text(q, max_results=10):
                    href = r.get("href", "")
                    title = r.get("title", "")
                    if any(s in href.lower() for s in skip):
                        continue
                    if href not in [u[0] for u in urls]:
                        urls.append((href, title))
                    if len(urls) >= 5:
                        break
                if len(urls) >= 5:
                    break
    except Exception as e:
        console.print(Panel(f"Search failed: {e}", style="bright_yellow", expand=False))
        fallback = console.input(
            "  [bold cyan]Enter a URL manually instead:[/bold cyan] "
        ).strip()
        if fallback:
            run_custom_url(fallback)
        return

    if not urls:
        console.print(Panel(
            "No x402 sites found in search.\n"
            "Try Option 4 to test a specific URL.",
            style="bright_yellow",
            expand=False
        ))
        return

    console.print()
    table = Table(show_header=True, style="dim white", box=None)
    table.add_column("#", style="bold magenta")
    table.add_column("URL", style="bright_cyan", max_width=50)
    table.add_column("Title", style="dim white")
    for i, (href, title) in enumerate(urls, 1):
        table.add_row(str(i), href[:50], title[:40])
    console.print(table)

    console.print()
    pick = console.input(
        "  [bold cyan]Select a site to test with Secure Agent[/bold cyan] [dim][1-5][/dim] or [dim][b] back[/dim]: "
    ).strip().lower()
    if pick == "b" or not pick.isdigit():
        return
    idx = int(pick) - 1
    if idx < 0 or idx >= len(urls):
        console.print("  [bold bright_red]Invalid selection.[/bold bright_red]")
        return

    target = urls[idx][0]
    console.print()
    run_custom_url(target)


def run_custom_url(url):
    step(f"Probing: [cyan]{url}[/cyan]")
    result, status = fetch_402(url)
    if status == "server_down":
        console.print(Panel("Connection failed.", style="bold bright_red", expand=False))
        return
    if status == "not_402":
        step(f"HTTP {result.status_code}", "dim white", "*")
        console.print(Panel(result.text[:500], style="dim white", expand=False))
        return
    step("x402 paywall detected!", "bold bright_green", "✓")
    run_protected(url)


if __name__ == "__main__":
    check_env()
    show_header()
    main_menu()
