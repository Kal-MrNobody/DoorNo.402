import sys
import os

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), "..", "..", "sdk", "python"
))

from dotenv import load_dotenv
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


def demo_menu():
    pass


def run_custom():
    pass


def run_search():
    pass


if __name__ == "__main__":
    check_env()
    show_header()
    main_menu()

