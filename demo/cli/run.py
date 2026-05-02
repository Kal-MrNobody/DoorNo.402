"""DoorNo.402 CLI — Security demo for x402 payments."""

import sys
import os
import time
import asyncio

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), "..", "..", "sdk", "python"
))

import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich import box
from web3 import Web3

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    
console = Console()

# Config
AGENT_ADDRESS = os.environ.get("AGENT_ADDRESS", "")
PRIVATE_KEY = os.environ.get("AGENT_PRIVATE_KEY", "")
USDC_CONTRACT = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
RPC_URL = "https://sepolia.base.org"

SERVER_CONFIG = [
    {"name": "CryptoInsider", "url_env": "SERVER_CRYPTOINSIDER",
     "default": "http://localhost:3001", "slug": "bitcoin-etf-flows",
     "vuln": "VULN-01 Price Inflation"},
    {"name": "ChainPulse", "url_env": "SERVER_CHAINPULSE",
     "default": "http://localhost:3002", "slug": "ai-agents-onchain",
     "vuln": "VULN-04 Prompt Injection"},
    {"name": "BlockBrief", "url_env": "SERVER_BLOCKBRIEF",
     "default": "http://localhost:3003", "slug": "daily-briefing-1",
     "vuln": "VULN-05 Budget Drain"},
    {"name": "NodeTimes", "url_env": "SERVER_NODETIMES",
     "default": "http://localhost:3004", "slug": "node-sync-performance",
     "vuln": "VULN-02 Unknown Recipient"},
    {"name": "Web3Daily", "url_env": "SERVER_WEB3DAILY",
     "default": "http://localhost:3005", "slug": "mev-bots-extracted",
     "vuln": "VULN-06 TLS Downgrade"},
    {"name": "ComboAttack", "url_env": "SERVER_COMBO",
     "default": "http://localhost:3006", "slug": "zero-day-dump",
     "vuln": "ALL VULNS"},
]


def check_env():
    missing = []
    for key in ["AGENT_ADDRESS", "AGENT_PRIVATE_KEY"]:
        if not os.environ.get(key):
            missing.append(key)
    if missing:
        console.print(Panel(
            f"[red bold]Missing .env keys:[/] {', '.join(missing)}\n"
            "Copy .env.example to .env and fill in values.",
            border_style="red",
        ))
        sys.exit(1)


def get_balance():
    try:
        w3 = Web3(Web3.HTTPProvider(RPC_URL))
        abi = [{"name": "balanceOf", "type": "function",
                "inputs": [{"name": "a", "type": "address"}],
                "outputs": [{"type": "uint256"}],
                "stateMutability": "view"}]
        usdc = w3.eth.contract(
            address=Web3.to_checksum_address(USDC_CONTRACT), abi=abi)
        raw = usdc.functions.balanceOf(
            Web3.to_checksum_address(AGENT_ADDRESS)).call()
        return raw / 1_000_000
    except Exception:
        return -1


def show_header():
    os.system("cls" if os.name == "nt" else "clear")
    balance = get_balance()
    bal_str = f"{balance:.2f} USDC" if balance >= 0 else "unavailable"
    short = AGENT_ADDRESS[:6] + "..." + AGENT_ADDRESS[-4:] if AGENT_ADDRESS else "not set"
    kh = "connected" if os.environ.get("KEEPERHUB_API_KEY") else "not set"

    console.print(Panel(
        f"[bold]DoorNo.402[/]  --  The Security Layer Your Agent Needs\n"
        f"{'─' * 50}\n"
        f"Wallet: [bold yellow]{short}[/]          Balance: [bold green]{bal_str}[/]\n"
        f"KeeperHub: [bold blue]{kh}[/]          Network: Base Sepolia",
        border_style="dim white",
    ))


def check_server_alive(url):
    try:
        resp = httpx.get(url + "/", timeout=5)
        return True
    except Exception:
        return False


def get_server_url(srv):
    return os.environ.get(srv["url_env"], srv["default"])


async def fetch_402_payload(url):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
        if resp.status_code != 402:
            console.print(f"  Server returned HTTP {resp.status_code}, not 402")
            return None
        return resp.json()
    except Exception as e:
        console.print(Panel(f"[red]Connection error: {e}[/]", border_style="red"))
        return None


def show_402_details(details):
    table = Table(show_header=False, border_style="dim white", box=box.SIMPLE)
    table.add_column("Field", style="bold blue")
    table.add_column("Value")
    table.add_row("Description", details["description"])
    table.add_row("Demanded", f"[red bold]${details['amount_usd']:.2f} USDC[/]")
    table.add_row("Recipient", details["recipient"][:20] + "..." if len(details["recipient"]) > 20 else details["recipient"])
    table.add_row("Network", details["network"])
    console.print(Panel(table, title="402 Payment Required", border_style="dim white"))


def show_blocked_panel(reason, amount_usd):
    console.print(Panel(
        f"[red bold]{reason}[/]\n\n"
        f"[green]${amount_usd:.2f} USDC protected[/]\n"
        f"KeeperHub was never called.",
        border_style="red",
        title="[red bold]PAYMENT BLOCKED[/]",
    ))
    balance = get_balance()
    if balance >= 0:
        console.print(f"  [green]Wallet balance: {balance:.2f} USDC -- unchanged[/]")
    append_blocked_log(reason, amount_usd)


def show_execution_result(result, amount_usd):
    table = Table(show_header=False, border_style="dim white", box=box.SIMPLE)
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("ExecutionId", result.execution_id)
    table.add_row("Status", f"[green]{result.status}[/]")
    if result.tx_hash:
        table.add_row("TxHash", result.tx_hash)
    if result.tx_link:
        table.add_row("Basescan", result.tx_link)
    table.add_row("Amount", f"${amount_usd:.2f} USDC")
    console.print(table)


def append_blocked_log(reason, amount_usd):
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).isoformat()
    with open("blocked_payments.log", "a") as f:
        f.write(f"{ts} | BLOCKED | ${amount_usd:.2f} | {reason}\n")


def append_approved_log(result, amount_usd):
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).isoformat()
    with open("approved_payments.log", "a") as f:
        f.write(f"{ts} | APPROVED | ${amount_usd:.2f} | {result.tx_hash or 'pending'}\n")


async def run_unprotected(server_url, slug):
    from keeperhub_executor import extract_payment_details, execute_payment

    console.print(Panel(
        "Mode: UNPROTECTED\n"
        "Agent -> KeeperHub (no DoorNo.402 validation)",
        border_style="red",
    ))

    url = f"{server_url}/api/articles/{slug}"
    console.print(f"  [blue]Fetching:[/] {url}")

    payload = await fetch_402_payload(url)
    if not payload:
        return

    details = extract_payment_details(payload)
    show_402_details(details)

    # Skip actual KeeperHub call for combo attack ($999k)
    if details["amount_usd"] > 1000:
        console.print(Panel(
            f"[red bold]In a real unprotected scenario, KeeperHub would execute\n"
            f"this ${details['amount_usd']:,.2f} payment. Skipping to protect demo wallet.[/]",
            border_style="red",
        ))
        return

    # =========================================================================
    # 🚨 VULNERABILITY POINT 🚨
    # An unprotected agent forwards the request directly to KeeperHub here.
    # 
    # To secure this agent, you would uncomment the DoorNo.402 validation:
    # 
    # from doorno402 import protect
    # client = protect(client, daily_budget=5.00)
    # =========================================================================

    console.print("[red bold]No validation -- forwarding directly to KeeperHub...[/]")

    with console.status("KeeperHub executing..."):
        result = await execute_payment(
            recipient=details["recipient"],
            amount_usd=details["amount_usd"],
            token_address=details["token_address"],
        )

    if result.success:
        show_execution_result(result, details["amount_usd"])
        console.print(Panel(
            f"[red bold]Agent was robbed.[/]\n"
            f"KeeperHub executed ${details['amount_usd']:.2f} with zero validation.\n"
            f"DoorNo.402 would have blocked this.",
            border_style="red", title="Result",
        ))
        append_approved_log(result, details["amount_usd"])
    else:
        console.print(Panel(f"[red]KeeperHub error: {result.error}[/]", border_style="red"))


async def run_protected(server_url, slug):
    from keeperhub_executor import extract_payment_details, execute_payment

    console.print(Panel(
        "Mode: PROTECTED\n"
        "Agent -> DoorNo.402 validates -> KeeperHub executes if approved",
        border_style="green",
    ))

    url = f"{server_url}/api/articles/{slug}"
    console.print(f"  [blue]Fetching:[/] {url}")

    payload = await fetch_402_payload(url)
    if not payload:
        return

    details = extract_payment_details(payload)
    show_402_details(details)

    from doorno402 import protect

    console.print("\n  [yellow]Securing agent with DoorNo.402 (2 lines of code)...[/]")
    time.sleep(0.3)

    client = httpx.AsyncClient(timeout=10)
    
    # =========================================================================
    # DOORNO.402 PROTECTION LAYER
    # We wrap the client. It will automatically intercept and validate any 402s.
    # =========================================================================
    client = protect(client, daily_budget=5.00)

    console.print("  [blue]Executing request via protected client...[/]")
    resp = await client.get(url)
    
    if resp.status_code == 403:
        show_blocked_panel("DoorNo.402 blocked the payment (Security Policy)", details["amount_usd"])
        await client.aclose()
        return
        
    await client.aclose()

    # All checks passed internally by protect()
    console.print("\n  [green bold]DoorNo.402 approved -- forwarding to KeeperHub...[/]")

    with console.status("KeeperHub executing..."):
        result = await execute_payment(
            recipient=details["recipient"],
            amount_usd=details["amount_usd"],
            token_address=details["token_address"],
        )

    if result.success:
        show_execution_result(result, details["amount_usd"])
        console.print(Panel(
            "[green bold]Clean payment executed.[/]\n"
            "DoorNo.402 validated. KeeperHub executed on Base Sepolia.",
            border_style="green", title="Result",
        ))
        append_approved_log(result, details["amount_usd"])
    else:
        console.print(Panel(f"[red]KeeperHub error: {result.error}[/]", border_style="red"))


async def run_all_servers():
    console.print(Panel(
        "Running full attack suite against 6 servers\n"
        "Each server exploits a different vulnerability\n"
        "DoorNo.402 will attempt to block all 6 attacks",
        border_style="dim white",
    ))

    from keeperhub_executor import extract_payment_details
    results = []

    for i, srv in enumerate(SERVER_CONFIG, 1):
        url = get_server_url(srv)
        console.print(f"\n  [{i}/6] {srv['name']:16s} -- {srv['vuln']:25s} ", end="")

        if not check_server_alive(url):
            console.print("[yellow]OFFLINE[/]")
            results.append({"name": srv["name"], "vuln": srv["vuln"],
                            "result": "OFFLINE", "saved": 0})
            continue

        article_url = f"{url}/api/articles/{srv['slug']}"
        payload = await fetch_402_payload(article_url)
        if not payload:
            console.print("[yellow]NO 402[/]")
            results.append({"name": srv["name"], "vuln": srv["vuln"],
                            "result": "NO 402", "saved": 0})
            continue

        details = extract_payment_details(payload)

        # Run validation pipeline using 2 lines
        from doorno402 import protect
        import httpx

        client = httpx.AsyncClient(timeout=5)
        client = protect(client, daily_budget=5.00)
        
        blocked = False
        reason = ""
        
        resp = await client.get(article_url)
        if resp.status_code == 403:
            blocked = True
            reason = "Security Policy Violation"
            
        await client.aclose()

        if blocked:
            console.print("[red bold]BLOCKED[/]")
            results.append({"name": srv["name"], "vuln": srv["vuln"],
                            "result": "BLOCKED", "saved": details["amount_usd"]})
            append_blocked_log(reason, details["amount_usd"])
        else:
            console.print("[green bold]ALLOWED[/]")
            results.append({"name": srv["name"], "vuln": srv["vuln"],
                            "result": "ALLOWED", "saved": 0})

    # Results table
    console.print()
    table = Table(title="DoorNo.402 Scan Results", border_style="dim white", box=box.ROUNDED)
    table.add_column("Site", style="bold")
    table.add_column("Attack")
    table.add_column("Result")
    table.add_column("Saved", style="green")

    total_saved = 0
    blocked_count = 0
    for r in results:
        res_style = "[red bold]BLOCKED[/]" if r["result"] == "BLOCKED" else (
            "[yellow]OFFLINE[/]" if r["result"] == "OFFLINE" else "[green bold]ALLOWED[/]")
        saved_str = f"${r['saved']:,.2f}" if r["saved"] > 0 else "--"
        table.add_row(r["name"], r["vuln"], res_style, saved_str)
        total_saved += r["saved"]
        if r["result"] == "BLOCKED":
            blocked_count += 1

    table.add_section()
    table.add_row("[bold]Total[/]", f"[bold]{blocked_count}/6 blocked[/]", "", f"[bold green]${total_saved:,.2f}[/]")
    console.print(table)

    balance = get_balance()
    if balance >= 0:
        console.print(f"\n  [green]Wallet balance: {balance:.2f} USDC -- unchanged[/]")


def show_server_menu():
    console.print("\n  Pick an attack scenario for the Agent:\n")
    for i, srv in enumerate(SERVER_CONFIG, 1):
        console.print(f"  [bold blue][{i}][/]  {srv['name']:16s} -- {srv['vuln']}")
    console.print("  [dim][b]  Back to main menu[/]")
    return Prompt.ask("\n  Select", choices=[str(i) for i in range(1, 7)] + ["b"], default="b")


def show_server_action_menu(srv):
    url = get_server_url(srv)
    console.print(f"\n  {srv['name']} -- {srv['vuln']}")
    console.print(f"  {'─' * 40}")
    console.print(f"  Server: {url}")
    console.print()
    console.print("  [bold red][1][/]  Run UNSECURE Agent  -- agent pays blindly via KeeperHub")
    console.print("  [bold green][2][/]  Run SECURE Agent    -- DoorNo.402 blocks malicious payload")
    console.print("  [bold blue][3][/]  Side by side        -- run both, compare results")
    console.print("  [dim][b]  Back[/]")
    return Prompt.ask("\n  Select", choices=["1", "2", "3", "b"], default="b")


async def run_keeperhub_demo():
    console.print(Panel(
        "KeeperHub Integration Demo\n"
        "{'─' * 45}\n"
        "Flow: DoorNo.402 validates -> KeeperHub executes\n",
        border_style="dim white",
    ))
    console.print("  [bold blue][1][/]  Blocked payment  -- malicious server, KeeperHub never called")
    console.print("  [bold blue][2][/]  Approved payment  -- honest server, KeeperHub executes")
    console.print("  [dim][b]  Back[/]")

    choice = Prompt.ask("\n  Select", choices=["1", "2", "b"], default="b")
    if choice == "b":
        return

    if choice == "1":
        # Hit CryptoInsider (malicious)
        srv = SERVER_CONFIG[0]
        url = get_server_url(srv)
        if not check_server_alive(url):
            console.print(Panel(
                f"[red]Server not running: {url}[/]\n"
                f"Start it: cd demo/servers/cryptoinsider && node server.js",
                border_style="red",
            ))
            return
        await run_protected(url, srv["slug"])
        console.print("\n  [dim]KeeperHub was never called.[/]")

    elif choice == "2":
        # Use blog or honest payload
        blog_url = os.environ.get("BLOG_URL", "http://localhost:3000")
        url = f"{blog_url}/api/articles/bitcoin-etf-analysis"
        console.print(f"  [blue]Testing honest endpoint:[/] {url}")
        await run_protected(blog_url, "bitcoin-etf-analysis")


async def run_custom_url():
    url = Prompt.ask("\n  Enter x402 endpoint URL")
    if not url:
        return

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
    except Exception as e:
        console.print(Panel(f"[red]Connection error: {e}[/]", border_style="red"))
        return

    if resp.status_code == 200:
        console.print(f"  Server returned HTTP 200")
        console.print(Panel(resp.text[:500], title="Response Preview", border_style="dim white"))
        return
    elif resp.status_code != 402:
        console.print(f"  Server returned HTTP {resp.status_code}")
        return

    console.print("  [green]HTTP 402 detected[/]")

    from keeperhub_executor import extract_payment_details
    payload = resp.json()
    details = extract_payment_details(payload)
    show_402_details(details)

    protected = Prompt.ask("  Run with DoorNo.402 protection?", choices=["y", "n"], default="y")
    if protected == "y":
        # Extract base URL and slug
        await run_protected(url.rsplit("/", 1)[0].rsplit("/", 1)[0], url.rsplit("/", 1)[-1])
    else:
        await run_unprotected(url.rsplit("/", 1)[0].rsplit("/", 1)[0], url.rsplit("/", 1)[-1])


async def main_menu():
    while True:
        show_header()
        console.print("  DoorNo.402 -- Select a demo mode\n")
        console.print("  [bold blue][1][/]  Run all 6 servers       -- full attack suite + results table")
        console.print("  [bold blue][2][/]  Run Agent (Secure vs Unsecure) -- compare SECURE vs UNSECURE agent")
        console.print("  [bold blue][3][/]  KeeperHub demo           -- validated payment execution")
        console.print("  [bold blue][4][/]  Custom URL               -- test any x402 endpoint")
        console.print("  [dim][q]  Quit[/]")

        choice = Prompt.ask("\n  Select", choices=["1", "2", "3", "4", "q"], default="q")

        try:
            if choice == "1":
                await run_all_servers()
                Prompt.ask("\n  Press Enter to continue")

            elif choice == "2":
                pick = show_server_menu()
                if pick == "b":
                    continue
                srv = SERVER_CONFIG[int(pick) - 1]
                url = get_server_url(srv)
                if not check_server_alive(url):
                    console.print(Panel(
                        f"[red]Server not running: {url}[/]\n"
                        f"Start it: cd demo/servers/{srv['name'].lower()} && node server.js",
                        border_style="red",
                    ))
                    Prompt.ask("\n  Press Enter to continue")
                    continue

                action = show_server_action_menu(srv)
                if action == "b":
                    continue
                elif action == "1":
                    await run_unprotected(url, srv["slug"])
                elif action == "2":
                    await run_protected(url, srv["slug"])
                elif action == "3":
                    console.print("\n  [red bold]-- Without DoorNo.402 --[/]")
                    await run_unprotected(url, srv["slug"])
                    console.print(f"\n  {'─' * 50}\n")
                    console.print("  [green bold]-- With DoorNo.402 --[/]")
                    await run_protected(url, srv["slug"])
                Prompt.ask("\n  Press Enter to continue")

            elif choice == "3":
                await run_keeperhub_demo()
                Prompt.ask("\n  Press Enter to continue")

            elif choice == "4":
                await run_custom_url()
                Prompt.ask("\n  Press Enter to continue")

            elif choice == "q":
                console.print("\n  [dim]Shutting down...[/]")
                break

        except Exception as e:
            console.print(Panel(f"[red]Error: {e}[/]", border_style="red"))
            Prompt.ask("\n  Press Enter to continue")


if __name__ == "__main__":
    check_env()
    asyncio.run(main_menu())
