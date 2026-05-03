"""DoorNo.402 CLI — the security layer your agent needs."""

import sys
import os
import asyncio
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "sdk", "python"))

import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from rich.rule import Rule
from rich import box
from web3 import Web3

from agent_runner import (
    fetch_articles, fetch_402, fetch_content,
    score_articles, extract_402, keeperhub_pay,
)
from report_writer import generate_filename, write_report, gemini_synthesize

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

console = Console()

# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------

WALLET_ADDRESS = os.environ.get("KEEPERHUB_WALLET", "")
USDC_CONTRACT = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
RPC_URL = "https://sepolia.base.org"

SERVERS = [
    {"key": "SERVER_CRYPTOINSIDER",  "default": "https://cryptoinsider-nine.vercel.app",
     "name": "CryptoInsider",  "vuln": "Price Inflation"},
    {"key": "SERVER_CHAINPULSE",     "default": "https://chainpulse-chi.vercel.app",
     "name": "ChainPulse",     "vuln": "Prompt Injection"},
    {"key": "SERVER_BLOCKBRIEF",     "default": "https://blockbrief-rho.vercel.app",
     "name": "BlockBrief",     "vuln": "Budget Drain"},
    {"key": "SERVER_NODETIMES",      "default": "https://nodetimes.vercel.app",
     "name": "NodeTimes",      "vuln": "Unknown Recipient"},
    {"key": "SERVER_WEB3DAILY",      "default": "https://web3daily-alpha.vercel.app",
     "name": "Web3Daily",      "vuln": "TLS Downgrade"},
    {"key": "SERVER_COMBO",          "default": "https://combo-dusky.vercel.app",
     "name": "ComboAttack",    "vuln": "All Vulns"},
    {"key": "SERVER_CHAINWATCH",     "default": "https://chainwatch-tan.vercel.app",
     "name": "ChainWatch",     "vuln": "Honest server"},
]


def url_of(srv: dict) -> str:
    return os.environ.get(srv["key"], srv["default"])


# ---------------------------------------------------------------------------
# balance
# ---------------------------------------------------------------------------

def get_balance() -> float:
    try:
        w3 = Web3(Web3.HTTPProvider(RPC_URL))
        abi = [{"name": "balanceOf", "type": "function",
                "inputs": [{"name": "a", "type": "address"}],
                "outputs": [{"type": "uint256"}],
                "stateMutability": "view"}]
        c = w3.eth.contract(
            address=Web3.to_checksum_address(USDC_CONTRACT), abi=abi)
        raw = c.functions.balanceOf(
            Web3.to_checksum_address(WALLET_ADDRESS)).call()
        return raw / 1_000_000
    except Exception:
        return -1.0


# ---------------------------------------------------------------------------
# ascii header
# ---------------------------------------------------------------------------

HEADER_ART = r"""
  ██████╗  ██████╗  ██████╗ ██████╗ ███╗   ██╗ ██████╗       ██╗  ██╗  ██████╗ ██████╗
  ██╔══██╗██╔═══██╗██╔═══██╗██╔══██╗████╗  ██║██╔═══██╗      ██║  ██║ ██╔═══██╗╚════██╗
  ██║  ██║██║   ██║██║   ██║██████╔╝██╔██╗ ██║██║   ██║      ███████║ ██║   ██║ █████╔╝
  ██║  ██║██║   ██║██║   ██║██╔══██╗██║╚██╗██║██║   ██║ ██╗  ╚════██║ ██║   ██║██╔═══╝
  ██████╔╝╚██████╔╝╚██████╔╝██║  ██║██║ ╚████║╚██████╔╝ ╚═╝       ██║ ╚██████╔╝███████╗
  ╚═════╝  ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝           ╚═╝  ╚═════╝ ╚══════╝
""".strip("\n")



def _gradient_char(ch: str, col: int, total: int) -> str:
    """Color a single char with a cyan->blue->purple gradient."""
    if ch in (" ", "\n"):
        return ch
    t = col / max(total - 1, 1)
    if t < 0.5:
        r, g, b = 0, 255, 255                                # cyan
        r2, g2, b2 = 37, 99, 235                             # blue
        f = t / 0.5
    else:
        r, g, b = 37, 99, 235                                # blue
        r2, g2, b2 = 124, 58, 237                            # purple
        f = (t - 0.5) / 0.5
    cr = int(r + (r2 - r) * f)
    cg = int(g + (g2 - g) * f)
    cb = int(b + (b2 - b) * f)
    return f"[rgb({cr},{cg},{cb})]{ch}[/]"


def print_header():
    os.system("cls" if os.name == "nt" else "clear")
    lines = HEADER_ART.split("\n")
    max_col = max(len(l) for l in lines)
    for line in lines:
        colored = "".join(_gradient_char(c, i, max_col) for i, c in enumerate(line))
        console.print(colored, highlight=False)
    console.print()
    console.print("  [dim]The Security Layer Your Agent Needs[/]", justify="center")
    console.print(Rule(style="dim"))


def print_status():
    bal = get_balance()
    bal_s = f"{bal:.2f} USDC" if bal >= 0 else "unavailable"
    short = (WALLET_ADDRESS[:6] + "..." + WALLET_ADDRESS[-4:]) if WALLET_ADDRESS else "not configured"
    kh = "connected" if os.environ.get("KEEPERHUB_API_KEY") else "not set"
    console.print(
        f"  [dim]wallet:[/] [cyan]{short}[/]   [dim]|[/]   "
        f"[dim]balance:[/] [bold green]{bal_s}[/]   [dim]|[/]   "
        f"[dim]network:[/] Base Sepolia   [dim]|[/]   "
        f"[dim]keeperhub:[/] [bold blue]{kh}[/]"
    )
    console.print(Rule(style="dim"))


# ---------------------------------------------------------------------------
# menu
# ---------------------------------------------------------------------------

def show_menu():
    console.print()
    console.print("  [cyan][1][/]  [bold]research[/]          [dim]run autonomous agent research[/]")
    console.print("  [cyan][2][/]  [bold]attack suite[/]      [dim]test all 7 servers + results table[/]")
    console.print("  [cyan][3][/]  [bold]single server[/]     [dim]pick one server to demo[/]")
    console.print("  [cyan][4][/]  [bold]keeperhub[/]         [dim]validated payment execution demo[/]")
    console.print("  [cyan][q][/]  [bold]quit[/]")
    console.print()
    return Prompt.ask("  >", choices=["1", "2", "3", "4", "q"], default="q",
                      show_choices=False)


# ---------------------------------------------------------------------------
# research mode helpers
# ---------------------------------------------------------------------------

async def _visit_unprotected(client, base_url, topic, idx, total, domain):
    """Visit one server in unprotected mode. Returns result dict."""
    console.print(f"\n  [blue][{idx}/{total}] {domain}[/]")
    res = {"domain": domain, "url": base_url, "article": None,
           "content": None, "paid": False, "blocked": False,
           "amount": 0.0, "tx": "", "tx_link": "",
           "description": "", "error": None}

    arts = await fetch_articles(client, base_url)
    if not arts:
        console.print("        [red]no articles found[/]")
        res["error"] = "no articles"
        return res

    console.print("        fetching article list...")
    pick = score_articles(arts, topic)
    res["article"] = pick.get("title", "?")
    slug = pick.get("slug", "")
    console.print(f'        selected: "{res["article"]}"')

    url = f"{base_url}/api/articles/{slug}"
    r = await fetch_402(client, url)
    if not r:
        res["error"] = "connection failed"
        console.print("        [red]connection failed[/]")
        return res

    if r["status"] == 200:
        data = r["payload"]
        res["content"] = data.get("content") or str(data)[:200]
        console.print("        free access — no payment needed")
        return res

    if r["status"] != 402:
        console.print(f"        [yellow]unexpected HTTP {r['status']}[/]")
        return res

    det = extract_402(r["payload"])
    res["amount"] = det["amount"]
    res["description"] = det["description"]
    desc_short = det["description"][:50]

    if det["amount"] > 1000:
        console.print(f"        [red]402 received — ${det['amount']:,.2f} (skipped, too high)[/]")
        res["paid"] = False
        return res

    console.print(
        f'        [red]402 received — paying ${det["amount"]:.2f} '
        f'(description said "{desc_short}")[/]')

    pay = await keeperhub_pay(det["recipient"], det["amount"], det["token"])
    if not pay["success"]:
        console.print(f"        [red]payment failed: {pay['error']}[/]")
        res["error"] = pay["error"]
        return res

    res["paid"] = True
    res["tx"] = pay["tx_hash"]
    res["tx_link"] = pay["tx_link"]
    tx_short = pay["tx_hash"][:10] + "..." + pay["tx_hash"][-8:] if pay["tx_hash"] else ""
    console.print(f"        [dim cyan]tx: {tx_short}[/]")
    console.print(f"        [dim cyan]basescan: {pay['tx_link']}[/]")

    content = await fetch_content(client, url, pay["tx_hash"])
    if content:
        res["content"] = content
        console.print("        content received — adding to research")
    return res


async def _visit_protected(client, base_url, topic, idx, total, domain):
    """Visit one server in protected mode. Returns result dict."""
    from doorno402 import protect

    console.print(f"\n  [blue][{idx}/{total}] {domain}[/]")
    res = {"domain": domain, "url": base_url, "article": None,
           "content": None, "paid": False, "blocked": False,
           "amount": 0.0, "tx": "", "tx_link": "",
           "description": "", "error": None, "saved": 0.0}

    arts = await fetch_articles(client, base_url)
    if not arts:
        console.print("        [red]no articles found[/]")
        res["error"] = "no articles"
        return res

    console.print("        fetching article list...")
    pick = score_articles(arts, topic)
    res["article"] = pick.get("title", "?")
    slug = pick.get("slug", "")
    console.print(f'        selected: "{res["article"]}"')

    url = f"{base_url}/api/articles/{slug}"

    # first get raw 402 to know the amount before protect() blocks it
    raw_r = await client.get(url)
    if raw_r.status_code == 200:
        data = raw_r.json()
        res["content"] = data.get("content") or str(data)[:200]
        console.print("        free access — no payment needed")
        return res

    if raw_r.status_code == 402:
        det = extract_402(raw_r.json())
        res["amount"] = det["amount"]
        res["description"] = det["description"]
        console.print("        402 received")

    # now run through protect()
    guarded = httpx.AsyncClient(timeout=15, follow_redirects=True)
    guarded = protect(guarded, daily_budget=5.00)

    resp = await guarded.get(url)
    await guarded.aclose()

    if resp.status_code == 403:
        res["blocked"] = True
        res["saved"] = res["amount"]
        desc = res["description"][:40]
        inflation = ""
        if res["amount"] > 0.02:
            inflation = f" — description ${0.01:.2f}, demanded ${res['amount']:.2f}"
        console.print(f"        [red bold]doorno.402: BLOCKED[/]")
        console.print(f"        [red]reason: security policy violation{inflation}[/]")
        console.print(f"        [green]saved: ${res['amount']:.2f}[/]")
        console.print("        content: unavailable (payment blocked)")
        return res

    # approved
    console.print(f"        [green bold]doorno.402: approved — ${res['amount']:.2f} matches description[/]")
    console.print("        forwarding to keeperhub...")

    pay = await keeperhub_pay(
        det["recipient"], det["amount"], det["token"])
    if not pay["success"]:
        console.print(f"        [red]payment failed: {pay['error']}[/]")
        res["error"] = pay["error"]
        return res

    res["paid"] = True
    res["tx"] = pay["tx_hash"]
    res["tx_link"] = pay["tx_link"]
    tx_short = pay["tx_hash"][:10] + "..." + pay["tx_hash"][-8:] if pay["tx_hash"] else ""
    console.print(f"        [dim cyan]tx: {tx_short}[/]")
    console.print(f"        [dim cyan]basescan: {pay['tx_link']}[/]")

    content = await fetch_content(client, url, pay["tx_hash"])
    if content:
        res["content"] = content
        console.print("        content received — adding to research")
    return res


# ---------------------------------------------------------------------------
# option 1 — research
# ---------------------------------------------------------------------------

async def research_mode():
    console.print("\n  [bold]research mode[/]")
    console.print(Rule(style="dim"))

    topic = Prompt.ask("  [bold]topic[/] ")
    if not topic.strip():
        return

    url_input = Prompt.ask(
        "  [bold]urls[/]  [dim](space separated, enter for all 7)[/]",
        default="")
    if url_input.strip():
        urls = url_input.strip().split()
    else:
        urls = [url_of(s) for s in SERVERS]

    mode_choice = Prompt.ask(
        "  [bold]mode[/]  [dim][1] unprotected  [2] protected  [3] compare[/]",
        choices=["1", "2", "3"], default="1")

    if mode_choice == "3":
        await _run_research(topic, urls, "unprotected")
        console.print("\n")
        Prompt.ask("  [dim]press enter to run protected mode[/]")
        os.system("cls" if os.name == "nt" else "clear")
        await _run_research(topic, urls, "protected")
        await _show_comparison()
        return

    mode = "unprotected" if mode_choice == "1" else "protected"
    await _run_research(topic, urls, mode)


async def _run_research(topic: str, urls: list, mode: str):
    console.print(f"\n  [bold]running {mode} research...[/]")
    if mode == "unprotected":
        console.print("  [dim]agent has no payment security[/]")
    else:
        console.print("  [dim]doorno.402 active — all payments validated[/]")
    console.print(Rule(style="dim"))

    client = httpx.AsyncClient(timeout=15, follow_redirects=True)
    results = []
    total = len(urls)

    for i, url in enumerate(urls, 1):
        domain = url.rstrip("/").split("//")[-1].split(".")[0]
        try:
            if mode == "unprotected":
                r = await _visit_unprotected(client, url.rstrip("/"), topic, i, total, domain)
            else:
                r = await _visit_protected(client, url.rstrip("/"), topic, i, total, domain)
            results.append(r)
        except Exception as e:
            console.print(f"        [red]error: {e}[/]")
            results.append({"domain": domain, "error": str(e)})

    await client.aclose()

    # summary table
    _print_summary_table(results, mode)

    # report
    with console.status("[dim]generating synthesis...[/]", spinner="dots"):
        sources = [r for r in results if r.get("content")]
        synthesis = await gemini_synthesize(topic, sources)

    path = generate_filename(mode)
    write_report(path, topic, mode, results, synthesis)
    rel_path = os.path.relpath(path)
    word_count = len(synthesis.split())

    console.print(f"\n  [dim]report saved to[/] [cyan]{rel_path}[/]")



def _print_summary_table(results: list, mode: str):
    console.print()
    table = Table(box=box.SIMPLE, border_style="dim")
    table.add_column("Server", style="bold")
    table.add_column("Vulnerability")

    if mode == "unprotected":
        table.add_column("Paid", style="red")
        table.add_column("Transaction", style="dim cyan")
        total_spent = 0.0
        for r in results:
            if r.get("error") and not r.get("paid"):
                table.add_row(r["domain"], "", "error", "")
                continue
            amt = f"${r.get('amount',0):.2f}" if r.get("paid") else "skipped"
            tx = (r.get("tx","")[:10] + "..." + r.get("tx","")[-8:]) if r.get("tx") else "-"
            vuln = next((s["vuln"] for s in SERVERS
                        if r["domain"] in url_of(s)), "")
            table.add_row(r["domain"], vuln, amt, tx)
            if r.get("paid"):
                total_spent += r.get("amount", 0)
        console.print(table)
        bal = get_balance()
        bal_s = f"{bal:.2f}" if bal >= 0 else "?"
        console.print(
            f"\n  [dim]total spent:[/] [red]${total_spent:.2f} USDC[/]   "
            f"[dim]|[/]   [dim]wallet:[/] {bal_s} USDC remaining")
    else:
        table.add_column("Result")
        table.add_column("Saved", style="green")
        total_saved = 0.0
        blocked = 0
        for r in results:
            if r.get("error") and not r.get("blocked") and not r.get("paid"):
                table.add_row(r["domain"], "", "error", "")
                continue
            vuln = next((s["vuln"] for s in SERVERS
                        if r["domain"] in url_of(s)), "")
            if r.get("blocked"):
                table.add_row(r["domain"], vuln,
                              "[red bold]BLOCKED[/]",
                              f"${r.get('saved',0):.2f}")
                total_saved += r.get("saved", 0)
                blocked += 1
            else:
                table.add_row(r["domain"], vuln,
                              "[green bold]APPROVED[/]", "-")
        console.print(table)
        total = len([r for r in results if not r.get("error")])
        approved = total - blocked
        console.print(
            f"\n  [dim]total blocked:[/] [red]{blocked}/{total}[/]   "
            f"[dim]|[/]   [dim]total saved:[/] [green]${total_saved:,.2f} USDC[/]")
        console.print(
            f"  [dim]total approved:[/] [green]{approved}/{total}[/]")


async def _show_comparison():
    console.print()
    table = Table(title="comparison summary", box=box.SIMPLE, border_style="dim")
    table.add_column("Without DoorNo.402", style="red")
    table.add_column("With DoorNo.402", style="green")
    table.add_row("all payments executed", "only honest payments approved")
    table.add_row("wallet drained", "wallet safe")
    console.print(table)


# ---------------------------------------------------------------------------
# option 2 — attack suite
# ---------------------------------------------------------------------------

async def attack_suite():
    console.print("\n  [bold]attack suite[/]")
    console.print("  [dim]testing all 7 servers with doorno.402 protection[/]")
    console.print(Rule(style="dim"))

    client = httpx.AsyncClient(timeout=15, follow_redirects=True)
    results = []

    for i, srv in enumerate(SERVERS, 1):
        base = url_of(srv)
        domain = srv["name"]
        try:
            r = await _visit_protected(
                client, base, "security test", i, len(SERVERS), domain)
            results.append(r)
        except Exception as e:
            console.print(f"        [red]error: {e}[/]")
            results.append({"domain": domain, "error": str(e)})

    await client.aclose()
    _print_summary_table(results, "protected")


# ---------------------------------------------------------------------------
# option 3 — single server
# ---------------------------------------------------------------------------

async def single_server():
    console.print("\n  [bold]single server[/]")
    console.print(Rule(style="dim"))
    for i, s in enumerate(SERVERS, 1):
        console.print(f"  [cyan][{i}][/]  [bold]{s['name']:16s}[/]  [dim]{s['vuln']}[/]")
    console.print("  [cyan][b][/]  [dim]back[/]")
    console.print()

    pick = Prompt.ask("  >", choices=[str(i) for i in range(1, 8)] + ["b"],
                      default="b", show_choices=False)
    if pick == "b":
        return

    srv = SERVERS[int(pick) - 1]
    base = url_of(srv)
    console.print(f"\n  [bold]{srv['name']}[/] — {srv['vuln']}")
    console.print(f"  [dim]{base}[/]")
    console.print()
    console.print("  [cyan][1][/]  unprotected")
    console.print("  [cyan][2][/]  protected")
    console.print("  [cyan][3][/]  side by side")
    console.print("  [cyan][b][/]  [dim]back[/]")

    action = Prompt.ask("  >", choices=["1", "2", "3", "b"],
                        default="b", show_choices=False)
    if action == "b":
        return

    client = httpx.AsyncClient(timeout=15, follow_redirects=True)
    if action == "1":
        await _visit_unprotected(client, base, "demo", 1, 1, srv["name"])
    elif action == "2":
        await _visit_protected(client, base, "demo", 1, 1, srv["name"])
    elif action == "3":
        console.print("\n  [red bold]-- without doorno.402 --[/]")
        await _visit_unprotected(client, base, "demo", 1, 1, srv["name"])
        console.print(f"\n  {'─' * 50}")
        console.print("  [green bold]-- with doorno.402 --[/]")
        await _visit_protected(client, base, "demo", 1, 1, srv["name"])
    await client.aclose()


# ---------------------------------------------------------------------------
# option 4 — keeperhub demo
# ---------------------------------------------------------------------------

async def keeperhub_demo():
    console.print("\n  [bold]keeperhub integration demo[/]")
    console.print(Rule(style="dim"))
    console.print("  [dim]flow: doorno.402 validates -> keeperhub executes[/]")
    console.print()
    console.print("  [cyan][1][/]  [bold]blocked demo[/]    [dim]malicious server, keeperhub never called[/]")
    console.print("  [cyan][2][/]  [bold]approved demo[/]   [dim]honest server, keeperhub executes[/]")
    console.print("  [cyan][b][/]  [dim]back[/]")
    console.print()

    choice = Prompt.ask("  >", choices=["1", "2", "b"],
                        default="b", show_choices=False)
    if choice == "b":
        return

    client = httpx.AsyncClient(timeout=15, follow_redirects=True)
    if choice == "1":
        srv = SERVERS[0]  # CryptoInsider (malicious)
        await _visit_protected(client, url_of(srv), "demo", 1, 1, srv["name"])
        console.print("\n  [dim]keeperhub was never called[/]")
    elif choice == "2":
        srv = SERVERS[6]  # ChainWatch (honest)
        await _visit_protected(client, url_of(srv), "demo", 1, 1, srv["name"])
    await client.aclose()


# ---------------------------------------------------------------------------
# main loop
# ---------------------------------------------------------------------------

async def main():
    while True:
        print_header()
        print_status()
        choice = show_menu()

        try:
            if choice == "1":
                await research_mode()
            elif choice == "2":
                await attack_suite()
            elif choice == "3":
                await single_server()
            elif choice == "4":
                await keeperhub_demo()
            elif choice == "q":
                console.print("\n  [dim]shutting down...[/]")
                break
        except Exception as e:
            console.print(f"\n  [red]error: {e}[/]")

        console.print()
        Prompt.ask("  [dim]press enter to continue[/]")


if __name__ == "__main__":
    asyncio.run(main())
