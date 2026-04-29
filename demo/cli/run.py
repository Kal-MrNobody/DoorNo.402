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
    pass


def run_custom():
    pass


def run_search():
    pass


if __name__ == "__main__":
    check_env()
    show_header()
    main_menu()

