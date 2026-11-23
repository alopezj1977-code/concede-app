# CONSEDE Executive Front

## Visual direction
The application follows the 4MSFTS command-center reference supplied for CONCEDE:
- Deep navy navigation rail and light executive workspace.
- Teal primary accent, with green, gold and red reserved for distinct business stages.
- White KPI surfaces, restrained borders and shadows, compact executive typography.
- Responsive command-center layout with a five-part overview and an executive attention panel.

## Implemented entry points
- `executive_front.py`: shared presentation tokens and command-center rendering.
- `app.py`: functional sidebar navigation for Centro de mando, Motor de leads and Mailing.
- `mailing_ui.py`: operational workspace with separate Contacts, Campaigns, Microsoft 365 and approval/send steps.

## Data integrity
The command-center dashboard displays only live CONCEDE run metrics for Base, Perfil and AAA/AA. Radar and Mailing cards identify modules/workflows; they do not invent activity counts. The dashboard is presentation-only and does not alter `core.py`, `concede_v3.json`, score weights, priority bands or results.

## Mailing release gates
- Neon persistence must be initialized successfully before importing contacts, saving drafts or sending.
- Workspace isolation and current recipient eligibility are checked by the persistence layer.
- Microsoft 365 delegated authentication remains restricted to `C@4msfts.com`.
- Human approval remains required immediately before sending.
- CI covers compilation, Microsoft Graph service regression tests and Mailing store/workspace tests.
- Deployment and live Microsoft 365 / Neon validation remain separate release checks; CI success alone is not production certification.
