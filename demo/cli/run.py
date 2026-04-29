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
        
        if choice in ("1", "2", "3"):
            console.print()
            console.print("  [bold cyan]Select Attack Scenario:[/bold cyan]")
            console.print("  [bold magenta]1.[/bold magenta] [white]Price Inflation[/white]        [dim]($0.01 description, $50.00 demanded)[/dim]")
            console.print("  [bold magenta]2.[/bold magenta] [white]Unknown Recipient[/white]      [dim](No ENS, fresh wallet)[/dim]")
            console.print("  [bold magenta]3.[/bold magenta] [white]Prompt Injection[/white]       [dim](Jailbreak description)[/dim]")
            console.print("  [bold magenta]4.[/bold magenta] [white]Budget Drain[/white]           [dim]($0.09 repeating charges)[/dim]")
            console.print("  [bold magenta]5.[/bold magenta] [white]Full Combo[/white]             [dim](All attacks at once)[/dim]")
            console.print("  [bold magenta]6.[/bold magenta] [white]Cryptology Blog[/white]        [dim](Original VULN-01 demo)[/dim]")
            
            scen_choice = console.input("  [bold magenta]>[/bold magenta] ").strip()
            
            if scen_choice == "1": url = "http://localhost:4000/vuln01"
            elif scen_choice == "2": url = "http://localhost:4000/vuln02"
            elif scen_choice == "3": url = "http://localhost:4000/vuln04"
            elif scen_choice == "4": url = "http://localhost:4000/vuln05"
            elif scen_choice == "5": url = "http://localhost:4000/combo"
            elif scen_choice == "6": url = f"{BLOG_URL}/api/articles/bitcoin-etf-analysis"
            else:
                console.print("  [bold red]Invalid scenario selection.[/bold red]")
                time.sleep(1)
                continue

            if choice == "1":
                run_unprotected(url)
            elif choice == "2":
                run_protected(url)
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


def _detect_attack_type(url, described, demanded, inflation):
    """Detect which attack is being demonstrated based on URL and data."""
    if "/vuln04" in url or "/combo" in url:
        if "SYSTEM" in str(described) or inflation > 1000:
            return "injection", "Agent processed a PROMPT INJECTION payload. The jailbreak description tricked the LLM into approving a malicious payment."
    if "/vuln02" in url:
        return "unknown_recipient", "Agent paid an UNKNOWN WALLET with no ENS name, no on-chain history. Funds sent to a potentially malicious address."
    if "/vuln05" in url:
        return "budget_drain", "Agent fell victim to BUDGET DRAIN. Small repeated charges slowly emptied the wallet without triggering any alarm."
    if inflation > 5:
        return "price_inflation", f"Agent fell victim to PRICE INFLATION exploit. Description claimed ${described:.2f} but protocol demanded ${demanded:.2f} ({inflation:,.0f}% inflation)."
    return "unknown", "Agent processed a potentially malicious x402 payment without any security checks."


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
            "Ensure attack server is running: node demo/attack-server/server.js",
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

    # Get real balance BEFORE the transaction
    before = get_balance()

    # Check if wallet has enough to pay
    if before < demanded:
        step(f"Wallet has ${before:.2f} but attack demands ${demanded:.2f}", "bright_red", "!")
        step("Agent WOULD pay if it had funds -- vulnerability confirmed", "bright_red", "!")
        time.sleep(0.5)

        # Still send what we can to prove the exploit works
        actual_raw = int(before * 1_000_000) - 1000  # leave tiny gas buffer
        if actual_raw <= 0:
            console.print(Panel(
                f"Wallet is empty. Cannot demonstrate on-chain drain.\n"
                f"The attack demanded ${demanded:.2f} -- agent would have paid it all.",
                style="bold bright_red",
                expand=False
            ))
            attack_type, failure_msg = _detect_attack_type(url, described, demanded, inflation)
            console.print(Panel(
                f"CRITICAL FAILURE: {failure_msg}",
                style="bold bright_red",
                expand=False
            ))
            return
        transfer_amount = actual_raw
        step(f"Draining entire wallet: ${actual_raw / 1_000_000:.2f} USDC", "bright_red", "!")
    else:
        transfer_amount = result["raw_amount"]

    step("Signing Ethereum transaction...", "bright_yellow")
    time.sleep(0.8)

    try:
        account = Account.from_key(PRIVATE_KEY)
        tx = usdc.functions.transfer(
            Web3.to_checksum_address(result["pay_to"]), transfer_amount
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

        if receipt.status:
            step("Transaction confirmed on Base Sepolia", "bright_green", "✓")
        else:
            step("Transaction reverted on-chain", "bright_red", "✗")
        console.print(f"    [dim cyan]Tx Hash: {tx_hash.hex()}[/dim cyan]")
        link = f"https://sepolia.basescan.org/tx/{tx_hash.hex()}"
        console.print(f"    [dim white]View on Explorer: [underline]{link}[/underline][/dim white]")
    except Exception as e:
        step(f"Transaction failed: {e}", "bright_red", "✗")

    time.sleep(0.3)

    after = get_balance()
    show_balance(before, after, "unprotected")

    attack_type, failure_msg = _detect_attack_type(url, described, demanded, inflation)
    console.print(Panel(
        f"CRITICAL FAILURE: {failure_msg}",
        style="bold bright_red",
        expand=False
    ))


def run_protected(url):
    console.print()
    step("Initializing secure agent [DoorNo.402 SDK loaded]...", "bright_magenta")
    time.sleep(0.6)
    step(f"Requesting resource: [cyan]{url}[/cyan]")
    time.sleep(0.4)

    result, status = fetch_402(url)
    if status == "server_down":
        console.print(Panel(
            "Target server unreachable.\n"
            "Ensure attack server is running: node demo/attack-server/server.js",
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
    from doorno402.validators.injection import validate_injection
    from doorno402.validators.ens_verifier import calculate_trust_score
    from doorno402.validators.budget import BudgetTracker
    from rich.padding import Padding

    described = extract_price(result["description"]) or 0.0
    demanded = result["demanded"]
    inflation = ((demanded - described) / described * 100) if described else 0

    show_payment_table(described, demanded, inflation)
    time.sleep(0.5)

    console.print()
    step("⚡ DoorNo.402 intercepting protocol execution...", "bright_magenta")
    time.sleep(0.8)

    blocked = False
    checks_passed = 0

    # ── CHECK 1: Prompt Injection ──
    step("Scanning description for prompt injection...", "bright_cyan", "1")
    time.sleep(0.4)
    inj_result = validate_injection(result["data"])
    if inj_result.get("injection_detected"):
        patterns = ", ".join(inj_result.get("patterns_matched", []))
        console.print(Padding(Panel(
            f"[bold]INJECTION DETECTED[/bold]\n"
            f"Patterns: {patterns}\n"
            f"Action: Description sanitized before LLM processing",
            style="bold bright_yellow",
            expand=False
        ), (0, 0, 0, 4)))
        step("Malicious payload stripped from description", "bright_yellow", "⚠")
    else:
        step("No injection detected ✓", "bright_green", "✓")
    checks_passed += 1
    time.sleep(0.3)

    # ── CHECK 2: Price Inflation ──
    step("Validating price integrity...", "bright_cyan", "2")
    time.sleep(0.4)
    price_result = validate_price(result["data"])
    if not price_result["valid"]:
        console.print(Padding(Panel(
            f"[bold]PRICE INFLATION BLOCKED[/bold]\n"
            f"{price_result['reason']}",
            style="bold bright_red",
            expand=False
        ), (0, 0, 0, 4)))
        step("Payment BLOCKED — price is fraudulent", "bright_red", "✗")
        blocked = True
    else:
        step(f"Price valid — ${described:.2f} matches protocol demand ✓", "bright_green", "✓")
        checks_passed += 1
    time.sleep(0.3)

    # ── CHECK 3: ENS Trust Score (only if price passed) ──
    if not blocked:
        step("Calculating ENS trust score for recipient...", "bright_cyan", "3")
        time.sleep(0.4)
        pay_to = result.get("pay_to", "")
        trust = calculate_trust_score(
            pay_to=pay_to,
            price_valid=price_result["valid"],
        )
        score_color = "bright_green" if trust.action == "allow" else (
            "bright_yellow" if trust.action == "flag" else "bright_red"
        )
        breakdown_lines = "\n".join(
            f"  {k}: {v}" for k, v in trust.breakdown.items()
        )

        if trust.action == "block":
            console.print(Padding(Panel(
                f"[bold]UNTRUSTED RECIPIENT BLOCKED[/bold]\n"
                f"Score: {trust.trust_score}/90\n"
                f"ENS: {trust.ens_name or 'NONE'}\n"
                f"{breakdown_lines}",
                style="bold bright_red",
                expand=False
            ), (0, 0, 0, 4)))
            step(f"Payment BLOCKED — trust score {trust.trust_score}/90", "bright_red", "✗")
            blocked = True
        elif trust.action == "flag":
            console.print(Padding(Panel(
                f"[bold]RECIPIENT FLAGGED[/bold]\n"
                f"Score: {trust.trust_score}/90\n"
                f"ENS: {trust.ens_name or 'NONE'}\n"
                f"{breakdown_lines}",
                style="bold bright_yellow",
                expand=False
            ), (0, 0, 0, 4)))
            step(f"Flagged for review — trust score {trust.trust_score}/90", "bright_yellow", "⚠")
            checks_passed += 1
        else:
            step(f"Recipient trusted — score {trust.trust_score}/90 ✓", "bright_green", "✓")
            checks_passed += 1
        time.sleep(0.3)

    # ── CHECK 4: Budget (only if not already blocked) ──
    if not blocked:
        step("Checking daily budget...", "bright_cyan", "4")
        time.sleep(0.4)
        tracker = BudgetTracker(daily_limit=5.00)
        budget_status = tracker.check(demanded)
        if not budget_status.allowed:
            console.print(Padding(Panel(
                f"[bold]BUDGET LIMIT EXCEEDED[/bold]\n"
                f"{budget_status.reason}",
                style="bold bright_red",
                expand=False
            ), (0, 0, 0, 4)))
            step("Payment BLOCKED — would exceed daily budget", "bright_red", "✗")
            blocked = True
        else:
            step(f"Budget OK — ${demanded:.2f} within $5.00 daily limit ✓", "bright_green", "✓")
            checks_passed += 1
        time.sleep(0.3)

    # ── Summary ──
    console.print()
    before = get_balance()

    if blocked:
        show_balance(before, before, "protected")
        console.print(Panel(
            f"THREAT NEUTRALIZED: DoorNo.402 blocked this attack. ${demanded:.2f} saved.",
            style="bold bright_green",
            expand=False
        ))
    else:
        show_balance(before, before, "protected")
        step("All 4 security checks passed — payment would proceed", "bright_green", "✓")

    console.print()
    step("Appending forensic data to blocked_payments.log...", "dim white", "»")
    ts = time.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    log_line = (
        f"{ts} | {url} | described=${described:.2f} | "
        f"demanded=${demanded:.2f} | blocked={blocked}\n"
    )
    with open("blocked_payments.log", "a") as f:
        f.write(log_line)
    time.sleep(0.3)

    try:
        with open("blocked_payments.log") as f:
            lines = f.readlines()
            last = lines[-1].strip() if lines else ""
        console.print(Padding(Panel(last, style="dim white", expand=False), (0, 0, 0, 2)))
    except FileNotFoundError:
        pass


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
