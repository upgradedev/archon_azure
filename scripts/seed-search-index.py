"""
seed-search-index.py — Create and populate the archon-knowledge AI Search index.

The index is the Foundry IQ grounding knowledge base used by NarratorAgent.
It contains Greek accounting and payroll regulation reference documents:
  - IKA/EFKA contribution rate tables (Law 4387/2016)
  - Greek VAT law N.2859/2000
  - IFRS standards relevant to payroll and financial reporting (IAS 1, IAS 19)
  - Greek Income Tax Code (N.4172/2013) key provisions

Usage:
    pip install azure-search-documents
    python scripts/seed-search-index.py

Environment variables required:
    AZURE_SEARCH_ENDPOINT   — https://<name>.search.windows.net
    AZURE_SEARCH_KEY        — admin key
"""

import os
import json
import uuid
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    SemanticConfiguration,
    SemanticSearch,
    SemanticPrioritizedFields,
    SemanticField,
)
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

# ── Configuration ─────────────────────────────────────────────────────────────

ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
KEY = os.environ["AZURE_SEARCH_KEY"]
INDEX_NAME = os.environ.get("AZURE_AI_SEARCH_INDEX", "archon-knowledge")

# ── Knowledge documents ───────────────────────────────────────────────────────

DOCUMENTS = [

    # ── IKA / EFKA Employer Contribution Rates ─────────────────────────────

    {
        "id": "ika-efka-employer-rates-2025",
        "title": "ΕΦΚΑ Εισφορές Εργοδότη 2025 — IKA/EFKA Employer Contribution Rates",
        "category": "IKA_EFKA",
        "source": "Νόμος 4387/2016, ΦΕΚ 85/Α/12-05-2016 — Law 4387/2016",
        "language": "el",
        "content": (
            "Εισφορές ΕΦΚΑ εργοδότη επί μικτών αποδοχών (2025):\n"
            "- Κύρια σύνταξη εργοδότη: 13.33%\n"
            "- Κύρια σύνταξη εργαζόμενου: 6.67%\n"
            "- Ασθένεια σε είδος εργοδότη: 4.30%\n"
            "- Ασθένεια σε είδος εργαζόμενου: 2.15%\n"
            "- Ασθένεια σε χρήμα εργοδότη: 0.25%\n"
            "- Ασθένεια σε χρήμα εργαζόμενου: 0.40%\n"
            "- ΕΤΕΑΕΠ εργοδότη: 3.25%\n"
            "- ΕΤΕΑΕΠ εργαζόμενου: 3.50%\n"
            "- ΟΑΕΔ (ανεργία) εργοδότη: 2.49%\n"
            "- ΟΑΕΔ (ανεργία) εργαζόμενου: 1.07%\n"
            "- ΕΤΕΑ εργοδότη: 0.24%\n"
            "Σύνολο εισφορών εργοδότη: περίπου 25.06%\n"
            "Σύνολο εισφορών εργαζόμενου: περίπου 13.87%\n"
            "Συνολικό εργοδοτικό κόστος ανά υπάλληλο = Μικτές αποδοχές × 1.2506\n\n"
            "Employer EFKA contributions on gross salary (2025):\n"
            "Main pension employer: 13.33%. Health in-kind employer: 4.30%. "
            "Health cash employer: 0.25%. ETEAEP employer: 3.25%. "
            "OAED unemployment employer: 2.49%. ETEA employer: 0.24%. "
            "Total employer rate: ~25.06% on top of gross salary.\n"
            "Total employer cost = gross salary × 1.2506.\n"
            "A bank transfer confirmation shows only the net salary paid; "
            "the true employer payroll cost is ~25% higher than the bank confirmation amount."
        ),
    },

    {
        "id": "ika-efka-employee-rates-2025",
        "title": "ΕΦΚΑ Εισφορές Εργαζόμενου 2025 — Employee Contribution Rates",
        "category": "IKA_EFKA",
        "source": "Νόμος 4387/2016 — Law 4387/2016",
        "language": "el",
        "content": (
            "Εισφορές εργαζόμενου ΕΦΚΑ επί μικτών αποδοχών:\n"
            "- Κύρια σύνταξη: 6.67%\n"
            "- Ασθένεια σε είδος: 2.15%\n"
            "- Ασθένεια σε χρήμα: 0.40%\n"
            "- ΕΤΕΑΕΠ: 3.50%\n"
            "- ΟΑΕΔ: 1.07%\n"
            "Σύνολο εισφορών εργαζόμενου: ~13.87%\n"
            "Καθαρές αποδοχές = Μικτές × (1 - 0.1387) - φόρος εισοδήματος\n\n"
            "Employee contributions reduce gross salary by ~13.87% before income tax. "
            "Net salary paid by bank transfer = gross minus employee contributions minus withholding tax. "
            "The employer payroll cost (gross + employer contributions) is materially higher "
            "than the net bank transfer amount."
        ),
    },

    {
        "id": "ika-efka-payroll-gap-explanation",
        "title": "Χάσμα Μισθοδοσίας: Τραπεζική Επιβεβαίωση vs Πραγματικό Κόστος",
        "category": "IKA_EFKA",
        "source": "Αρχή Λογιστικής — Archon Payroll Intelligence",
        "language": "el",
        "content": (
            "Το χάσμα μεταξύ τραπεζικής επιβεβαίωσης και πραγματικού εργοδοτικού κόστους:\n\n"
            "Παράδειγμα για μικτές αποδοχές €5,000/μήνα:\n"
            "- Μικτές αποδοχές: €5,000\n"
            "- Εισφορές εργοδότη (~25.06%): €1,253\n"
            "- Συνολικό εργοδοτικό κόστος: €6,253\n"
            "- Εισφορές εργαζόμενου (~13.87%): €694\n"
            "- Φόρος εισοδήματος (εκτίμηση): €559\n"
            "- Καθαρές αποδοχές (τραπεζικό έμβασμα): €3,747\n\n"
            "Η τραπεζική επιβεβαίωση δείχνει €3,747 αλλά το πραγματικό κόστος είναι €6,253. "
            "Διαφορά: 67% μεγαλύτερο από το τραπεζικό έμβασμα, ή ~28% υποεκτίμηση "
            "αν υπολογίσουμε ως ποσοστό του εργοδοτικού κόστους.\n\n"
            "The bank confirmation understates true payroll cost by approximately 28%. "
            "Accurate P&L accounting must use the employer cost total from the payroll register, "
            "not the net bank transfer. This is the core insight of the Archon Event Linker: "
            "fusing bank confirmation + payroll register + payslips into one accurate payroll event."
        ),
    },

    # ── Greek VAT Law ──────────────────────────────────────────────────────

    {
        "id": "vat-law-2859-2000-rates",
        "title": "ΦΠΑ — Συντελεστές Νόμος 2859/2000",
        "category": "VAT",
        "source": "Νόμος 2859/2000 ΦΠΑ, άρθρα 21-22 — Greek VAT Code",
        "language": "el",
        "content": (
            "Συντελεστές ΦΠΑ βάσει Ν.2859/2000 (ισχύοντες 2025):\n"
            "- Κανονικός συντελεστής: 24% (άρθρο 21 παρ. 1)\n"
            "- Μειωμένος συντελεστής: 13% (τρόφιμα, φάρμακα, ξενοδοχεία, θέατρα)\n"
            "- Υπερμειωμένος συντελεστής: 6% (βιβλία, εφημερίδες, εισιτήρια θεάτρου)\n"
            "- Μηδενικός συντελεστής: 0% (εξαγωγές, ενδοκοινοτικές παραδόσεις)\n\n"
            "Παρακράτηση ΦΠΑ σε υπηρεσίες πληροφορικής: 24%\n"
            "Τιμολόγια τεχνολογικών υπηρεσιών (SaaS, cloud, consulting): 24%\n\n"
            "VAT rates under Law 2859/2000: standard 24%, reduced 13%, super-reduced 6%. "
            "IT services, SaaS subscriptions, and professional services invoiced to Greek businesses "
            "are subject to 24% VAT. Input VAT on business expenses is recoverable for VAT-registered entities."
        ),
    },

    {
        "id": "vat-reverse-charge-b2b",
        "title": "ΦΠΑ — Αντιστροφή Επιβάρυνσης B2B Υπηρεσίες",
        "category": "VAT",
        "source": "Νόμος 2859/2000 άρθρο 14, Οδηγία 2006/112/ΕΚ",
        "language": "el",
        "content": (
            "Αντιστροφή επιβάρυνσης ΦΠΑ για υπηρεσίες από χώρες ΕΕ και τρίτες χώρες:\n"
            "Τιμολόγια από AWS, Google Cloud, Microsoft Azure, Anthropic, OpenAI "
            "σε ελληνική επιχείρηση: εφαρμόζεται αντιστροφή επιβάρυνσης (reverse charge). "
            "Η ελληνική εταιρεία αυτολογίζει ΦΠΑ 24% ως εισροή και εκροή ταυτόχρονα — "
            "μηδενική ταμειακή επίπτωση για επιχειρήσεις με πλήρες δικαίωμα έκπτωσης.\n\n"
            "Reverse charge mechanism applies to B2B services received from EU/non-EU providers "
            "(e.g., AWS, Azure, Google Cloud, OpenAI API invoices). "
            "Greek VAT-registered company self-assesses 24% VAT as both input and output — "
            "net zero cash impact for fully taxable businesses. "
            "These invoices appear in both the input VAT and output VAT registers."
        ),
    },

    # ── IFRS / IAS Standards ───────────────────────────────────────────────

    {
        "id": "ias-19-employee-benefits",
        "title": "IAS 19 — Παροχές σε Εργαζόμενους / Employee Benefits",
        "category": "IFRS",
        "source": "IAS 19 Employee Benefits — IASB",
        "language": "en",
        "content": (
            "IAS 19 Employee Benefits — key provisions for payroll accounting:\n\n"
            "Short-term employee benefits (due within 12 months): recognised as an expense "
            "and a liability when the employee has rendered service. Includes wages, salaries, "
            "social security contributions (IKA/EFKA employer contributions in Greece), "
            "paid annual leave, and paid sick leave.\n\n"
            "Employer social security contributions (EFKA ~25.06% in Greece) must be included "
            "in the total employee benefit expense recognised in the P&L. "
            "Recording only the net salary paid (bank transfer) understates the payroll expense "
            "and violates IAS 19 paragraph 10.\n\n"
            "Correct P&L entry: Debit Payroll Expense (gross + employer contributions), "
            "Credit Bank (net salary), Credit EFKA Payable (employee + employer contributions), "
            "Credit Withholding Tax Payable.\n\n"
            "Under IAS 19, the full employer cost — not the bank transfer amount — "
            "is the correct measure of the employee benefit expense for P&L purposes."
        ),
    },

    {
        "id": "ias-1-presentation-pnl",
        "title": "IAS 1 — Παρουσίαση Οικονομικών Καταστάσεων / Presentation of Financial Statements",
        "category": "IFRS",
        "source": "IAS 1 Presentation of Financial Statements — IASB",
        "language": "en",
        "content": (
            "IAS 1 requires financial statements to present a true and fair view of "
            "the entity's financial position and performance.\n\n"
            "Income Statement / P&L presentation:\n"
            "- Revenue: recognised when earned (invoiced services delivered)\n"
            "- Operating expenses: includes staff costs at full employer cost (IAS 19)\n"
            "- Staff costs must include: gross salaries + employer social security contributions\n"
            "- Depreciation and amortisation disclosed separately\n"
            "- Finance costs (bank charges, interest) disclosed separately\n\n"
            "For Greek SMBs, IAS 1 and the Greek Accounting Standards (Law 4308/2014) "
            "both require that staff costs in the P&L reflect the full employer payroll cost, "
            "not merely the net salary transferred to employee bank accounts.\n\n"
            "Operating profit (EBIT) = Revenue - Cost of Sales - Operating Expenses\n"
            "Net profit = EBIT - Finance costs - Tax\n"
            "EBITDA = EBIT + Depreciation + Amortisation"
        ),
    },

    # ── Greek Accounting Standards (N.4308/2014) ───────────────────────────

    {
        "id": "greek-accounting-law-4308-2014",
        "title": "Ελληνικά Λογιστικά Πρότυπα — Νόμος 4308/2014",
        "category": "GREEK_ACCOUNTING",
        "source": "Νόμος 4308/2014 ΦΕΚ 251/Α/24-11-2014",
        "language": "el",
        "content": (
            "Ελληνικά Λογιστικά Πρότυπα (ΕΛΠ) — Ν.4308/2014:\n\n"
            "Άρθρο 17 — Κατάσταση αποτελεσμάτων:\n"
            "Οι δαπάνες προσωπικού περιλαμβάνουν:\n"
            "α) Μισθοί και ημερομίσθια\n"
            "β) Εργοδοτικές εισφορές (ΕΦΚΑ, ΟΑΕΔ κ.λπ.)\n"
            "γ) Λοιπές παροχές προσωπικού\n\n"
            "Η ορθή λογιστική αντιμετώπιση απαιτεί καταχώρηση του συνολικού "
            "εργοδοτικού κόστους (μικτές + εισφορές εργοδότη) ως δαπάνη, "
            "όχι μόνο του καθαρού ποσού εμβάσματος.\n\n"
            "Άρθρο 30 — Μικρές οντότητες (κύκλος εργασιών έως €1.500.000): "
            "απλοποιημένες υποχρεώσεις κατάρτισης λογιστικών καταστάσεων.\n\n"
            "Τιμολόγιο (άρθρο 8): εκδίδεται για κάθε παράδοση αγαθών ή παροχή υπηρεσιών. "
            "Περιλαμβάνει: ΑΦΜ εκδότη/λήπτη, ημερομηνία, περιγραφή, αξία, ΦΠΑ."
        ),
    },

    # ── Greek Income Tax ───────────────────────────────────────────────────

    {
        "id": "greek-income-tax-4172-2013-withholding",
        "title": "Παρακράτηση Φόρου Μισθωτών — Ν.4172/2013",
        "category": "INCOME_TAX",
        "source": "Νόμος 4172/2013 Κώδικας Φορολογίας Εισοδήματος, άρθρα 15-16",
        "language": "el",
        "content": (
            "Κλίμακα φορολογίας εισοδήματος μισθωτών (Ν.4172/2013, άρθρο 15):\n"
            "- €0 – €10,000: 9%\n"
            "- €10,001 – €20,000: 22%\n"
            "- €20,001 – €30,000: 28%\n"
            "- €30,001 – €40,000: 36%\n"
            "- Πάνω από €40,000: 44%\n\n"
            "Αφορολόγητο όριο: €8,636 για μισθωτούς χωρίς εξαρτώμενα τέκνα "
            "(μειώνεται για εισοδήματα > €12,000).\n\n"
            "Παρακράτηση φόρου (άρθρο 16): ο εργοδότης παρακρατεί μηνιαίως "
            "τον αναλογούντα φόρο βάσει ετησιοποιημένων αποδοχών.\n\n"
            "Withholding tax rates for salaried employees in Greece (Law 4172/2013): "
            "progressive scale 9%-44%. Employer withholds monthly and remits to tax authority. "
            "Net salary = gross - employee EFKA contributions - withholding tax."
        ),
    },

    # ── Cash Flow & Banking ────────────────────────────────────────────────

    {
        "id": "cash-flow-payroll-reconciliation",
        "title": "Ταμειακές Ροές Μισθοδοσίας — Συμφωνία Τράπεζας",
        "category": "CASH_FLOW",
        "source": "IAS 7 Statement of Cash Flows — IASB",
        "language": "en",
        "content": (
            "IAS 7 Cash Flow Statement — payroll-related cash flows:\n\n"
            "Operating cash outflows related to payroll:\n"
            "1. Net salary payments (bank transfer to employees) — appears in bank confirmation\n"
            "2. EFKA contributions (employee + employer) — paid monthly to EFKA portal\n"
            "3. Withholding income tax — paid monthly to AADE (tax authority)\n\n"
            "The bank confirmation shows item 1 only. "
            "Total payroll cash outflow = net salaries + EFKA contributions + withholding tax. "
            "All three items must appear in the cash flow statement under operating activities.\n\n"
            "Bank statement reconciliation: the bank confirmation amount for payroll "
            "represents only the net salary transfer. EFKA and tax payments are "
            "separate bank transactions (typically mid-month and end of following month).\n\n"
            "For accurate cash flow reporting, cross-reference: "
            "bank confirmation (net salary date) + EFKA payment confirmation + tax payment."
        ),
    },

]

# ── Create index ──────────────────────────────────────────────────────────────

def create_index(client: SearchIndexClient) -> None:
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="title", type=SearchFieldDataType.String, analyzer_name="el.microsoft"),
        SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="el.microsoft"),
        SimpleField(name="category", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="source", type=SearchFieldDataType.String),
        SimpleField(name="language", type=SearchFieldDataType.String, filterable=True),
    ]

    semantic_config = SemanticConfiguration(
        name="archon-semantic",
        prioritized_fields=SemanticPrioritizedFields(
            title_field=SemanticField(field_name="title"),
            content_fields=[SemanticField(field_name="content")],
            keywords_fields=[SemanticField(field_name="category")],
        ),
    )

    index = SearchIndex(
        name=INDEX_NAME,
        fields=fields,
        semantic_search=SemanticSearch(
            default_configuration_name="archon-semantic",
            configurations=[semantic_config],
        ),
    )

    client.create_or_update_index(index)
    print(f"Index '{INDEX_NAME}' created/updated.")


# ── Upload documents ──────────────────────────────────────────────────────────

def upload_documents(endpoint: str, key: str) -> None:
    search_client = SearchClient(
        endpoint=endpoint,
        index_name=INDEX_NAME,
        credential=AzureKeyCredential(key),
    )
    result = search_client.upload_documents(documents=DOCUMENTS)
    succeeded = sum(1 for r in result if r.succeeded)
    print(f"Uploaded {succeeded}/{len(DOCUMENTS)} documents.")
    for r in result:
        status = "OK" if r.succeeded else f"FAIL ({r.error_message})"
        print(f"  {r.key}: {status}")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    credential = AzureKeyCredential(KEY)
    index_client = SearchIndexClient(endpoint=ENDPOINT, credential=credential)

    print(f"Seeding index: {INDEX_NAME}")
    print(f"Endpoint: {ENDPOINT}")
    print()

    create_index(index_client)
    upload_documents(ENDPOINT, KEY)

    print()
    print("Done. Verify at:")
    print(f"  {ENDPOINT}/indexes/{INDEX_NAME}/docs/$count?api-version=2024-07-01")
