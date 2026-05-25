#!/usr/bin/env python3
# Standard library
import os
import sys
from datetime import date, timedelta

# Third-party: CLI framework, env vars, Notion SDK, terminal UI
import click
from dotenv import load_dotenv
from notion_client import Client
from rich.console import Console
from rich.table import Table

# Reads NOTION_API_KEY from a .env file in the project root
load_dotenv()

# Hardcoded Notion database IDs — found in the database URL on notion.so
CONTACTS_DB_ID = "d87f84dc2ca046109a9eb0ce371ff690"
OUTREACH_LOG_DB_ID = "d956c7018ed04d2cbc48dcaa9b926ab8"

console = Console()


def get_client():
    # Fails fast if the API key is missing rather than letting Notion return a 401
    key = os.getenv("NOTION_API_KEY")
    if not key:
        console.print("[red]Error: NOTION_API_KEY not set. Add it to a .env file.[/red]")
        sys.exit(1)
    return Client(auth=key)


def extract(prop):
    # Notion returns properties as typed objects; this normalises any type to a plain string
    if not prop:
        return ""
    t = prop.get("type")
    if t == "title":
        return "".join(r["plain_text"] for r in prop["title"])
    if t == "rich_text":
        return "".join(r["plain_text"] for r in prop["rich_text"])
    if t == "email":
        return prop.get("email") or ""
    if t == "phone_number":
        return prop.get("phone_number") or ""
    if t == "url":
        return prop.get("url") or ""
    if t == "select":
        return prop["select"]["name"] if prop.get("select") else ""
    if t == "multi_select":
        return ", ".join(o["name"] for o in prop.get("multi_select", []))
    if t == "date":
        return prop["date"]["start"] if prop.get("date") else ""
    return ""


def prompt_date(label):
    # Loops until the user enters a valid ISO date or leaves it blank
    while True:
        val = click.prompt(f"{label} (YYYY-MM-DD, blank to skip)", default="")
        if not val:
            return ""
        try:
            date.fromisoformat(val)
            return val
        except ValueError:
            console.print("[red]Invalid date. Use format YYYY-MM-DD, e.g. 2026-06-01[/red]")


def find_contact(notion: Client, query: str):
    # Searches contacts by name; if multiple match, prompts the user to pick one
    results = notion.databases.query(
        database_id=CONTACTS_DB_ID,
        filter={"property": "Name", "title": {"contains": query}},
    )["results"]

    if not results:
        return None
    if len(results) == 1:
        return results[0]

    console.print(f"\n[yellow]Multiple matches for '{query}':[/yellow]")
    for i, r in enumerate(results, 1):
        name = extract(r["properties"]["Name"])
        company = extract(r["properties"]["Company"])
        console.print(f"  {i}. {name} ({company})")
    idx = click.prompt("Select number", type=int) - 1
    return results[idx] if 0 <= idx < len(results) else None


# --- CLI entry point ---
# Each function decorated with @cli.command() becomes a subcommand, e.g. `python crm.py add`

@click.group()
def cli():
    """Network Outreach CRM."""
    pass


@cli.command()
def add():
    """Add a new contact."""
    notion = get_client()
    console.print("\n[bold blue]Add New Contact[/bold blue]\n")

    name = click.prompt("Full name")
    email = click.prompt("Email", default="")
    phone = click.prompt("Phone", default="")
    linkedin = click.prompt("LinkedIn URL", default="")
    company = click.prompt("Company", default="")
    title = click.prompt("Job title", default="")
    industry = click.prompt(
        "Industry",
        type=click.Choice(["Tech", "Finance", "Healthcare", "Real Estate", "Media", "Consulting", "Other"]),
        default="Other",
    )
    location = click.prompt("Location", default="")
    source = click.prompt(
        "Source",
        type=click.Choice(["Referral", "LinkedIn", "Event", "Cold Outreach", "Inbound", "Other"]),
        default="Other",
    )
    status = click.prompt(
        "Status",
        type=click.Choice(["Active", "Dormant", "Converted", "Dead"]),
        default="Active",
    )
    tags_raw = click.prompt("Tags (investor, warm, cold, partner, client, advisor)", default="")
    notes = click.prompt("Notes", default="")
    followup = prompt_date("Next follow-up")

    # Build the properties dict — only include fields that have a value, since
    # sending an empty string to Notion can overwrite existing data with blanks
    props = {"Name": {"title": [{"text": {"content": name}}]}}
    if email:
        props["Email"] = {"email": email}
    if phone:
        props["Phone"] = {"phone_number": phone}
    if linkedin:
        props["LinkedIn"] = {"url": linkedin}
    if company:
        props["Company"] = {"rich_text": [{"text": {"content": company}}]}
    if title:
        props["Job Title"] = {"rich_text": [{"text": {"content": title}}]}
    if industry:
        props["Industry"] = {"select": {"name": industry}}
    if location:
        props["Location"] = {"rich_text": [{"text": {"content": location}}]}
    if source:
        props["Source"] = {"select": {"name": source}}
    if status:
        props["Status"] = {"select": {"name": status}}
    if notes:
        props["Notes"] = {"rich_text": [{"text": {"content": notes}}]}
    if followup:
        props["Next Follow-up"] = {"date": {"start": followup}}

    # Only allow known tag values to prevent typos creating junk options in Notion
    valid_tags = {"investor", "warm", "cold", "partner", "client", "advisor"}
    tags = [{"name": t.strip()} for t in tags_raw.split(",") if t.strip() in valid_tags]
    if tags:
        props["Tags"] = {"multi_select": tags}

    notion.pages.create(parent={"database_id": CONTACTS_DB_ID}, properties=props)
    console.print(f"\n[green]Contact '{name}' added.[/green]")


@cli.command()
def log():
    """Log an outreach touchpoint."""
    notion = get_client()
    console.print("\n[bold blue]Log Outreach[/bold blue]\n")

    query = click.prompt("Contact name (or partial)")
    contact = find_contact(notion, query)
    if not contact:
        console.print(f"[red]No contact found matching '{query}'[/red]")
        return

    contact_name = extract(contact["properties"]["Name"])
    console.print(f"[green]→ {contact_name}[/green]")

    summary = click.prompt("Summary (e.g. 'Intro email sent')")
    log_date = click.prompt("Date (YYYY-MM-DD)", default=date.today().isoformat())
    try:
        date.fromisoformat(log_date)
    except ValueError:
        console.print("[red]Invalid date. Use YYYY-MM-DD format.[/red]")
        return
    channel = click.prompt(
        "Channel",
        type=click.Choice(["Email", "LinkedIn", "Phone", "In-person", "Event", "Other"]),
    )
    direction = click.prompt(
        "Direction",
        type=click.Choice(["Outbound", "Inbound"]),
        default="Outbound",
    )
    response = click.prompt(
        "Response",
        type=click.Choice(["Yes", "No", "Pending", "N/A"]),
        default="Pending",
    )
    followup = prompt_date("Next follow-up")
    notes = click.prompt("Notes", default="")

    # Create a new row in the Outreach Log database linked back to the contact
    log_props = {
        "Summary": {"title": [{"text": {"content": summary}}]},
        "Contact": {"relation": [{"id": contact["id"]}]},
        "Channel": {"select": {"name": channel}},
        "Direction": {"select": {"name": direction}},
        "Response": {"select": {"name": response}},
        "Date": {"date": {"start": log_date}},
    }
    if notes:
        log_props["Notes"] = {"rich_text": [{"text": {"content": notes}}]}
    if followup:
        log_props["Next Follow-up"] = {"date": {"start": followup}}

    notion.pages.create(parent={"database_id": OUTREACH_LOG_DB_ID}, properties=log_props)

    # Also update the contact record so Last Contact and Next Follow-up stay current
    contact_updates = {"Last Contact": {"date": {"start": log_date}}}
    if followup:
        contact_updates["Next Follow-up"] = {"date": {"start": followup}}
    notion.pages.update(page_id=contact["id"], properties=contact_updates)

    console.print(f"\n[green]Logged '{summary}' for {contact_name}.[/green]")
    if followup:
        console.print(f"[blue]Next follow-up: {followup}[/blue]")


@cli.command("list")
@click.option("--status", "-s", help="Filter by status")
@click.option("--tag", "-t", help="Filter by tag")
def list_contacts(status, tag):
    """List all contacts."""
    notion = get_client()

    # Build filters dynamically so we can combine status and tag independently
    filters = []
    if status:
        filters.append({"property": "Status", "select": {"equals": status}})
    if tag:
        filters.append({"property": "Tags", "multi_select": {"contains": tag}})

    kwargs = {
        "database_id": CONTACTS_DB_ID,
        "sorts": [{"property": "Name", "direction": "ascending"}],
    }
    if len(filters) == 1:
        kwargs["filter"] = filters[0]
    elif len(filters) > 1:
        kwargs["filter"] = {"and": filters}

    pages = notion.databases.query(**kwargs)["results"]

    if not pages:
        console.print("[yellow]No contacts found.[/yellow]")
        return

    table = Table(header_style="bold blue")
    table.add_column("Name", min_width=20)
    table.add_column("Company", min_width=15)
    table.add_column("Status", min_width=10)
    table.add_column("Last Contact", min_width=12)
    table.add_column("Next Follow-up", min_width=14)
    table.add_column("Tags")

    for p in pages:
        pr = p["properties"]
        table.add_row(
            extract(pr.get("Name")),
            extract(pr.get("Company")),
            extract(pr.get("Status")),
            extract(pr.get("Last Contact")),
            extract(pr.get("Next Follow-up")),
            extract(pr.get("Tags")),
        )

    console.print(table)
    console.print(f"\n[dim]{len(pages)} contact(s)[/dim]")


@cli.command()
@click.argument("query")
def search(query):
    """Search contacts by name."""
    notion = get_client()
    pages = notion.databases.query(
        database_id=CONTACTS_DB_ID,
        filter={"property": "Name", "title": {"contains": query}},
    )["results"]

    if not pages:
        console.print(f"[yellow]No contacts found matching '{query}'.[/yellow]")
        return

    table = Table(header_style="bold blue")
    table.add_column("Name", min_width=20)
    table.add_column("Company", min_width=15)
    table.add_column("Email", min_width=22)
    table.add_column("Status", min_width=10)
    table.add_column("Next Follow-up", min_width=14)

    for p in pages:
        pr = p["properties"]
        table.add_row(
            extract(pr.get("Name")),
            extract(pr.get("Company")),
            extract(pr.get("Email")),
            extract(pr.get("Status")),
            extract(pr.get("Next Follow-up")),
        )

    console.print(table)


@cli.command()
@click.option("--days", "-d", default=7, show_default=True, help="Due within N days")
def followups(days):
    """Show contacts due for follow-up."""
    notion = get_client()
    today = date.today()
    end = today + timedelta(days=days)

    # Filters to contacts with a follow-up date set, due within the window, and not Dead
    pages = notion.databases.query(
        database_id=CONTACTS_DB_ID,
        filter={
            "and": [
                {"property": "Next Follow-up", "date": {"is_not_empty": True}},
                {"property": "Next Follow-up", "date": {"on_or_before": end.isoformat()}},
                {"property": "Status", "select": {"does_not_equal": "Dead"}},
            ]
        },
        sorts=[{"property": "Next Follow-up", "direction": "ascending"}],
    )["results"]

    if not pages:
        console.print(f"[green]No follow-ups due in the next {days} days.[/green]")
        return

    console.print(f"\n[bold]Follow-ups due within {days} days:[/bold]\n")
    table = Table(header_style="bold yellow")
    table.add_column("Due", min_width=12)
    table.add_column("Name", min_width=20)
    table.add_column("Company", min_width=15)
    table.add_column("Status", min_width=10)
    table.add_column("Last Contact", min_width=12)

    for p in pages:
        pr = p["properties"]
        due = extract(pr.get("Next Follow-up"))
        overdue = due and due < today.isoformat()
        due_display = f"[red]{due} ⚠[/red]" if overdue else due
        table.add_row(
            due_display,
            extract(pr.get("Name")),
            extract(pr.get("Company")),
            extract(pr.get("Status")),
            extract(pr.get("Last Contact")),
        )

    console.print(table)
    console.print(f"\n[dim]{len(pages)} contact(s)[/dim]")


@cli.command()
@click.argument("name")
def show(name):
    """Show contact details and full outreach history."""
    notion = get_client()
    contact = find_contact(notion, name)
    if not contact:
        console.print(f"[red]No contact found matching '{name}'[/red]")
        return

    pr = contact["properties"]
    console.print(f"\n[bold blue]{extract(pr.get('Name'))}[/bold blue]")
    console.print(f"[dim]{extract(pr.get('Job Title'))} @ {extract(pr.get('Company'))}[/dim]\n")

    for label, key in [
        ("Email", "Email"), ("Phone", "Phone"), ("LinkedIn", "LinkedIn"),
        ("Industry", "Industry"), ("Location", "Location"), ("Source", "Source"),
        ("Status", "Status"), ("Tags", "Tags"),
        ("Last Contact", "Last Contact"), ("Next Follow-up", "Next Follow-up"),
        ("Notes", "Notes"),
    ]:
        val = extract(pr.get(key))
        if val:
            console.print(f"  [bold]{label}:[/bold] {val}")

    # Fetch all outreach log entries that are related to this contact
    logs = notion.databases.query(
        database_id=OUTREACH_LOG_DB_ID,
        filter={"property": "Contact", "relation": {"contains": contact["id"]}},
        sorts=[{"property": "Date", "direction": "descending"}],
    )["results"]

    if not logs:
        console.print("\n[dim]No outreach logged yet.[/dim]")
        return

    console.print(f"\n[bold]Outreach History ({len(logs)} touchpoints):[/bold]\n")
    table = Table(header_style="bold")
    table.add_column("Date", min_width=12)
    table.add_column("Channel", min_width=10)
    table.add_column("Dir.", min_width=9)
    table.add_column("Summary", min_width=30)
    table.add_column("Response", min_width=10)
    table.add_column("Notes")

    for lg in logs:
        lp = lg["properties"]
        table.add_row(
            extract(lp.get("Date")),
            extract(lp.get("Channel")),
            extract(lp.get("Direction")),
            extract(lp.get("Summary")),
            extract(lp.get("Response")),
            extract(lp.get("Notes")),
        )

    console.print(table)


if __name__ == "__main__":
    cli()
