import sys
import os
import time

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), "..", "..", "sdk", "python"
))

import httpx
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


def show_header():
    os.system("cls" if os.name == "nt" else "clear")
    balance = get_balance()
    short_addr = AGENT_ADDRESS[:6] + "..." + AGENT_ADDRESS[-3:]
    content = (
        "[bold white]DoorNo.402[/bold white]\n"
        "x402 Payment Security SDK\n"
        "[dim]" + "-" * 49 + "[/dim]\n"
        f"Wallet: {short_addr}        "
        f"Balance: [bold cyan]{balance:.2f} USDC[/bold cyan]"
    )
    console.print(Panel(content, style="dim white", width=55))


def show_balance(before, after, mode="unprotected"):
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="dim")
    table.add_column(style="bold cyan")
    table.add_row("Before", f"{before:.2f} USDC")
    table.add_row("After", f"{after:.2f} USDC")
    diff = before - after
    if mode == "unprotected":
        table.add_row("Drained", f"[bold red]${diff:.2f}[/bold red]")
    else:
        table.add_row("Protected", f"[bold green]${diff:.2f} saved[/bold green]")
    console.print(Panel(table, title="[bold blue]Wallet[/bold blue]", style="dim white"))


def step(msg, style="yellow"):
    console.print(f"  [dim]--[/dim] [{style}]{msg}[/{style}]")


def show_payment_table(described, demanded, inflation):
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="dim", width=20)
    table.add_column(style="bold white")
    table.add_row("Description says", f"${described:.2f}")
    table.add_row("Protocol demands", f"[bold red]${demanded:.2f}[/bold red]")
    table.add_row("Inflation", f"[bold red]{inflation:,.0f}%[/bold red]")
    table.add_row("Threshold", "5%")
    console.print(Panel(
        table,
        title="[bold blue]Payment Analysis[/bold blue]",
        style="dim white"
    ))



def main_menu():
    while True:
        console.print()
        console.print("[bold blue]  Select an option:[/bold blue]")
        console.print("  [1] Demo Mode       -- attack demo against Cryptology blog")
        console.print("  [2] Custom URL      -- give the agent any URL to fetch")
        console.print("  [3] Find x402 Sites -- search for x402-enabled services")
        console.print("  [dim][q] Quit[/dim]")
        console.print()
        choice = console.input("[dim]>[/dim] ").strip().lower()
        if choice == "1":
            demo_menu()
        elif choice == "2":
            run_custom()
        elif choice == "3":
            run_search()
        elif choice == "q":
            console.print("[dim]bye[/dim]")
            break
        else:
            console.print("[bold red]invalid option[/bold red]")


def fetch_402(url):
    try:
        resp = httpx.get(url, timeout=10)
    except httpx.ConnectError:
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
    step("Connecting to Cryptology blog...")
    time.sleep(0.6)
    step(f"Fetching: {url}")
    time.sleep(0.4)

    result, status = fetch_402(url)
    if status == "server_down":
        console.print(Panel(
            "Blog server is not running.\n"
            "Start it with: cd demo/blog/backend && node server.js",
            style="bold red"
        ))
        return
    if status == "not_402":
        step(f"Server responded: {result.status_code} (no paywall)", "dim")
        return

    step("Server responded: 402 Payment Required", "bold red")
    time.sleep(0.3)

    from doorno402.validators.price import extract_price
    described = extract_price(result["description"]) or 0.0
    demanded = result["demanded"]
    inflation = ((demanded - described) / described * 100) if described else 0

    show_payment_table(described, demanded, inflation)
    time.sleep(0.5)

    step("Signing transaction...", "yellow")
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

    step("Transaction sent", "bold green" if receipt.status else "bold red")
    console.print(f"    [dim cyan]{tx_hash.hex()}[/dim cyan]")
    link = f"https://sepolia.basescan.org/tx/{tx_hash.hex()}"
    console.print(f"    [dim]{link}[/dim]")
    time.sleep(0.3)

    after = get_balance()
    before = after + demanded
    show_balance(before, after, "unprotected")
    console.print(Panel(
        "Agent was robbed. No validation was done.",
        style="bold red"
    ))


def demo_menu():
    while True:
        console.print()
        console.print("[bold blue]  Demo Mode:[/bold blue]")
        console.print("  [1] Unprotected  -- agent pays the fraudulent amount")
        console.print("  [2] Protected    -- DoorNo.402 blocks the payment")
        console.print("  [3] Side by side -- run both sequentially")
        console.print("  [dim][b] Back[/dim]")
        console.print()
        c = console.input("[dim]>[/dim] ").strip().lower()
        url = f"{BLOG_URL}/api/articles/bitcoin-etf-analysis"
        if c == "1":
            run_unprotected(url)
        elif c == "2":
            run_protected(url)
        elif c == "3":
            run_side_by_side(url)
        elif c == "b":
            break
        again = console.input("\n  Run again? [dim][y/n][/dim] ").strip().lower()
        if again != "y":
            break


def run_protected(url):
    console.print()
    step("Connecting to Cryptology blog...")
    time.sleep(0.6)
    step(f"Fetching: {url}")
    time.sleep(0.4)

    result, status = fetch_402(url)
    if status == "server_down":
        console.print(Panel(
            "Blog server is not running.\n"
            "Start it with: cd demo/blog/backend && node server.js",
            style="bold red"
        ))
        return
    if status == "not_402":
        step(f"Server responded: {result.status_code} (no paywall)", "dim")
        return

    step("Server responded: 402 Payment Required", "bold red")
    time.sleep(0.3)

    from doorno402.validators.price import extract_price, validate_price
    described = extract_price(result["description"]) or 0.0
    demanded = result["demanded"]
    inflation = ((demanded - described) / described * 100) if described else 0

    show_payment_table(described, demanded, inflation)
    time.sleep(0.5)

    step("DoorNo.402 intercepting...", "yellow")
    time.sleep(0.8)

    validation = validate_price(result["data"])

    if not validation["valid"]:
        console.print(Panel(
            validation["reason"],
            style="bold red"
        ))
        time.sleep(0.3)

        before = get_balance()
        show_balance(before, before, "protected")
        console.print(Panel(
            "Payment blocked. Wallet safe.",
            style="bold green"
        ))

        step("Writing to blocked_payments.log...", "dim")
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
            console.print(Panel(last, style="dim"))
        except FileNotFoundError:
            pass
    else:
        step("Payment approved by DoorNo.402 -- price is legitimate", "bold green")


def run_side_by_side(url):
    console.print()
    console.rule("[bold red]Without DoorNo.402[/bold red]", style="dim")
    run_unprotected(url)
    console.print()
    console.rule("[bold green]With DoorNo.402[/bold green]", style="dim")
    run_protected(url)


def run_custom():
    console.print()
    url = console.input("  [bold blue]Enter URL to fetch:[/bold blue] ").strip()
    if not url:
        return

    protected = console.input(
        "  Run with DoorNo.402 protection? [dim][y/n][/dim] "
    ).strip().lower() == "y"

    console.print()
    step(f"Fetching: {url}")
    time.sleep(0.4)

    result, status = fetch_402(url)
    if status == "server_down":
        console.print(Panel("Connection failed.", style="bold red"))
        return

    if status == "not_402":
        code = result.status_code
        step(f"Server responded: {code}", "dim")
        if code == 200:
            body = result.text[:500]
            console.print(Panel(body, title="[bold blue]Response[/bold blue]", style="dim white"))
        else:
            console.print(Panel(f"HTTP {code}", style="yellow"))
        return

    step("Server responded: 402 Payment Required", "bold red")
    time.sleep(0.3)

    if protected:
        run_protected(url)
    else:
        run_unprotected(url)


def run_search():
    console.print()
    step("Searching for x402-enabled services...", "yellow")

    try:
        from duckduckgo_search import DDGS
    except ImportError:
        console.print(Panel(
            "duckduckgo-search not installed.\n"
            "pip install duckduckgo-search",
            style="bold red"
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
        console.print(Panel(f"Search failed: {e}", style="yellow"))
        fallback = console.input(
            "  Enter a URL manually instead: "
        ).strip()
        if fallback:
            run_custom_url(fallback)
        return

    if not urls:
        console.print(Panel(
            "No x402 sites found in search.\n"
            "Try Option 2 to test a specific URL.",
            style="yellow"
        ))
        return

    table = Table(show_header=True, style="dim white")
    table.add_column("#", style="bold")
    table.add_column("URL", style="cyan", max_width=50)
    table.add_column("Title", style="dim")
    for i, (href, title) in enumerate(urls, 1):
        table.add_row(str(i), href[:50], title[:40])
    console.print(table)

    console.print()
    pick = console.input(
        "  Select a site to test [dim][1-5][/dim] or [dim][b] back[/dim]: "
    ).strip().lower()
    if pick == "b" or not pick.isdigit():
        return
    idx = int(pick) - 1
    if idx < 0 or idx >= len(urls):
        console.print("[bold red]invalid selection[/bold red]")
        return

    target = urls[idx][0]
    step(f"Testing: {target}")
    time.sleep(0.4)

    result, status = fetch_402(target)
    if status == "server_down":
        console.print(Panel("Connection failed.", style="bold red"))
        return
    if status == "not_402":
        code = result.status_code
        step(f"No x402 paywall -- got HTTP {code}", "dim")
        body = result.text[:500]
        console.print(Panel(body, title="[bold blue]Response[/bold blue]", style="dim white"))
        return

    step("x402 paywall detected!", "bold green")
    protected = console.input(
        "  Run with DoorNo.402 protection? [dim][y/n][/dim] "
    ).strip().lower() == "y"
    if protected:
        run_protected(target)
    else:
        run_unprotected(target)


def run_custom_url(url):
    step(f"Fetching: {url}")
    result, status = fetch_402(url)
    if status == "server_down":
        console.print(Panel("Connection failed.", style="bold red"))
        return
    if status == "not_402":
        step(f"HTTP {result.status_code}", "dim")
        console.print(Panel(result.text[:500], style="dim white"))
        return
    step("x402 paywall detected!", "bold green")
    run_protected(url)


if __name__ == "__main__":
    check_env()
    show_header()
    main_menu()

