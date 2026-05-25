# Network Outreach CRM

## What this is
A personal CRM for business development outreach. Contacts and outreach history live in Notion. A Python CLI and a local web dashboard are the interfaces.

## Notion databases
- **Contacts**: `d87f84dc2ca046109a9eb0ce371ff690`
- **Outreach Log**: `d956c7018ed04d2cbc48dcaa9b926ab8`

The Contacts database has a relation to Outreach Log. When a touchpoint is logged, the CLI auto-updates Last Contact and Next Follow-up on the contact record.

## Auth
A `.env` file in the project root holds the Notion API key:
```
NOTION_API_KEY=secret_...
```

## What's been built
- `crm.py` — Python CLI with commands: `add`, `log`, `list`, `search`, `followups`, `show`
- Uses `notion-client==2.2.1` (must pin to this version — 3.x broke the query API)

## What's left to build
A local web dashboard using **Streamlit** that reads directly from Notion and shows:
- Key metrics: total contacts, active contacts, follow-ups due this week
- Chart: contacts by status
- Chart: outreach by channel
- Table: follow-ups due this week
- Table: recent outreach activity

## Local setup (Mac)
```bash
cd ~/Documents/networkoutreach
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 crm.py list
```

To run the dashboard (once built):
```bash
streamlit run dashboard.py
```

## Dependencies
```
notion-client==2.2.1
click>=8.1.0
python-dotenv>=1.0.0
rich>=13.0.0
streamlit>=1.35.0
plotly>=5.0.0
pandas>=2.0.0
```

## File structure
```
networkoutreach/
├── crm.py          # CLI tool
├── dashboard.py    # Streamlit web dashboard (to be built)
├── requirements.txt
├── .env            # Notion API key (never commit this)
└── CLAUDE.md       # this file
```

## Notes
- User is non-technical, prefers VS Code over raw terminal
- Keep explanations simple and step-by-step
- The venv must be activated before running anything: `source venv/bin/activate`
