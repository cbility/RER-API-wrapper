from typing import TypedDict, Optional #typing
from selectolax.parser import HTMLParser # for parsing HTML

# region types

class OrganisationSummary(TypedDict):
    organisation_id: str
    name: str
    type: str
    task_count: int
    status: str
    user_status: str

class User(TypedDict):
    email: str
    full_name: str
    outstanding_tasks: int
    active_organisations: int


class OrganisationAddress(TypedDict):
    name: str
    address: str

class OrganisationContact(TypedDict):
    name: str
    email: str

class OrganisationTab(TypedDict):
    name: str
    url: str

class OrganisationDetail(TypedDict):
    organisation_id: str
    name: str
    type: str
    status: str
    address: OrganisationAddress
    contact: OrganisationContact
    tabs: list[OrganisationTab]

class OutputDataTask(TypedDict):
    task_id: str
    period: str
    station_name: str
    status: str
    url: str

class OutputDataTaskList(TypedDict):
    organisation_id: str
    tasks: list[OutputDataTask]

class StationDeclarationTask(TypedDict):
    declaration_type: str
    year: str
    url: str

class StationDeclarationTaskList(TypedDict):
    organisation_id: str
    tasks: list[StationDeclarationTask]

class CertificateTypeSummary(TypedDict):
    cert_type: str
    issued: int
    balance: Optional[int]
    breakdown_url: str
    history_url: str

class CertificatesOverview(TypedDict):
    organisation_id: str
    balance_period: str
    summaries: list[CertificateTypeSummary]

class CertificateBreakdownItem(TypedDict):
    action: str
    country: str
    station: str
    technology: str
    output_period: str
    count: int

class CertificateBreakdown(TypedDict):
    organisation_id: str
    cert_type: str
    items: list[CertificateBreakdownItem]

class CertificateHistoryMonth(TypedDict):
    month: str
    month_url: str
    transferred_in: int
    transferred_out: int

class CertificateHistory(TypedDict):
    organisation_id: str
    cert_type: str
    months: list[CertificateHistoryMonth]

# endregion types


# region parsers

def _parse_user(html: str) -> User:
    tree = HTMLParser(html)

    h1 = tree.css_first("h1.govuk-heading-xl")
    caption = h1.css_first("span.govuk-caption-l")
    email = caption.text(strip=True).split(",")[-1].strip()

    # Remove caption, links, and spans to isolate the full name
    caption.decompose()
    for node in h1.css("a"):
        node.decompose()
    for node in h1.css("span"):
        node.decompose()
    full_name = h1.text(strip=True)

    # Stats
    outstanding_tasks = 0
    active_organisations = 0
    for item in tree.css(".ofgem-rer-stat__item"):
        figure = item.css_first(".ofgem-rer-stat__figure")
        description = item.css_first(".ofgem-rer-stat__description")
        if figure and description:
            count_str = figure.text(strip=True)
            label = description.text(strip=True).lower()
            try:
                count = int(count_str.replace(",", ""))
            except ValueError:
                count = 0
            if "task" in label:
                outstanding_tasks = count
            elif "organisation" in label:
                active_organisations = count

    return User(
        email=email,
        full_name=full_name,
        outstanding_tasks=outstanding_tasks,
        active_organisations=active_organisations,
    )

def _parse_user_organisations(pages: list[str]) -> list[OrganisationSummary]:
    organisations: list[OrganisationSummary] = []
    for html in pages:
        tree = HTMLParser(html)
        for row in tree.css("table tr")[1:]:
            cells = row.css("td")
            if not cells:
                continue
            org_link = cells[0].css_first("a")
            org_id = ""
            if org_link:
                href = org_link.attrs.get("href", "")
                org_id = href.split("/Organisations/")[-1].split("/")[0]
            organisations.append(OrganisationSummary(
                organisation_id=org_id,
                name=cells[0].text(strip=True),
                type=cells[1].text(strip=True),
                task_count=int(cells[2].text(strip=True) or 0),
                status=cells[3].text(strip=True),
                user_status=cells[4].text(strip=True),
            ))
    return organisations

def _parse_organisation(html: str) -> OrganisationDetail:
    tree = HTMLParser(html)

    # Parse all definition lists by position
    dls = tree.css("dl")

    def dl_to_dict(dl) -> dict[str, str]:
        result: dict[str, str] = {}
        dts = dl.css("dt")
        dds = dl.css("dd")
        for dt, dd in zip(dts, dds):
            result[dt.text(strip=True)] = dd.text(separator=" ", strip=True)
        return result

    org_dict = dl_to_dict(dls[0]) if len(dls) > 0 else {}
    addr_dict = dl_to_dict(dls[1]) if len(dls) > 1 else {}
    contact_dict = dl_to_dict(dls[2]) if len(dls) > 2 else {}

    # Tab navigation
    tabs: list[OrganisationTab] = [
        OrganisationTab(name=a.text(strip=True), url=a.attrs.get("href", ""))
        for a in tree.css(".moj-sub-navigation a")
    ]

    return OrganisationDetail(
        organisation_id=org_dict.get("Organisation reference", ""),
        name=org_dict.get("Organisation name", ""),
        type=org_dict.get("Organisation type", ""),
        status=org_dict.get("Account status", ""),
        address=OrganisationAddress(
            name=addr_dict.get("Name", ""),
            address=addr_dict.get("Address", ""),
        ),
        contact=OrganisationContact(
            name=contact_dict.get("Name", ""),
            email=contact_dict.get("Email address", ""),
        ),
        tabs=tabs,
    )

def _parse_output_data_tasks(html: str, organisation_id: str) -> OutputDataTaskList:
    tree = HTMLParser(html)
    tasks: list[OutputDataTask] = []

    for row in tree.css("table tr")[1:]:
        cells = row.css("td")
        if len(cells) < 4:
            continue
        link = cells[0].css_first("a")
        url = link.attrs.get("href", "") if link else ""
        # Extract task ID from /Output/{uuid}/...
        task_id = ""
        url_parts = url.split("/")
        output_idx = next((i for i, p in enumerate(url_parts) if p == "Output"), None)
        if output_idx is not None and output_idx + 1 < len(url_parts):
            task_id = url_parts[output_idx + 1].split("?")[0]

        tasks.append(OutputDataTask(
            task_id=task_id,
            period=cells[0].text(strip=True),
            station_name=cells[1].text(strip=True),
            status=cells[3].text(strip=True),
            url=url,
        ))

    return OutputDataTaskList(organisation_id=organisation_id, tasks=tasks)

def _parse_station_declaration_tasks(html: str, organisation_id: str) -> StationDeclarationTaskList:
    tree = HTMLParser(html)
    tasks: list[StationDeclarationTask] = []

    for row in tree.css("table tr")[1:]:
        cells = row.css("td")
        if len(cells) < 2:
            continue
        link = cells[0].css_first("a")
        url = link.attrs.get("href", "") if link else ""
        tasks.append(StationDeclarationTask(
            declaration_type=cells[0].text(strip=True),
            year=cells[1].text(strip=True),
            url=url,
        ))

    return StationDeclarationTaskList(organisation_id=organisation_id, tasks=tasks)

def _parse_certificates_overview(html: str, organisation_id: str) -> CertificatesOverview:
    tree = HTMLParser(html)

    desc_el = tree.css_first(".ofgem-rer-stat__description")
    balance_period = desc_el.text(strip=True) if desc_el else ""

    summaries: list[CertificateTypeSummary] = []
    for grid_row in tree.css(".govuk-grid-row"):
        stat_el = grid_row.css_first(".ofgem-rer-stat__item")
        if not stat_el:
            continue

        h2 = stat_el.css_first("h2")
        if not h2:
            continue
        cert_type_label = h2.text(strip=True)  # e.g. "REGOs issued" or "ROCs issued"
        cert_type = "REGO" if "REGO" in cert_type_label else "ROC"

        # issued count: text of the strong figure after removing the h2
        figure_el = stat_el.css_first(".ofgem-rer-stat__figure")
        h2.decompose()
        try:
            issued = int(figure_el.text(strip=True).replace(",", "")) if figure_el else 0
        except ValueError:
            issued = 0

        # balance from dl/dd if present
        balance: Optional[int] = None
        dd = grid_row.css_first("dd")
        if dd:
            try:
                balance = int(dd.text(strip=True).replace(",", ""))
            except ValueError:
                balance = None

        # links
        links = grid_row.css("a.ofgem-rer-certificate-dashboard-summary__link")
        breakdown_url = links[0].attrs.get("href", "") if len(links) > 0 else ""
        history_url = links[1].attrs.get("href", "") if len(links) > 1 else ""

        summaries.append(CertificateTypeSummary(
            cert_type=cert_type,
            issued=issued,
            balance=balance,
            breakdown_url=breakdown_url,
            history_url=history_url,
        ))

    return CertificatesOverview(organisation_id=organisation_id, balance_period=balance_period, summaries=summaries)

def _parse_certificate_breakdown(html: str, organisation_id: str, cert_type: str) -> CertificateBreakdown:
    tree = HTMLParser(html)
    items: list[CertificateBreakdownItem] = []

    for row in tree.css("table tr")[1:]:
        cells = row.css("td")
        if len(cells) < 6:
            continue
        try:
            count = int(cells[5].text(strip=True).replace(",", ""))
        except ValueError:
            count = 0
        items.append(CertificateBreakdownItem(
            action=cells[0].text(strip=True),
            country=cells[1].text(strip=True),
            station=cells[2].text(strip=True),
            technology=cells[3].text(strip=True),
            output_period=cells[4].text(strip=True),
            count=count,
        ))

    return CertificateBreakdown(organisation_id=organisation_id, cert_type=cert_type, items=items)

def _parse_certificate_history(html: str, organisation_id: str, cert_type: str) -> CertificateHistory:
    tree = HTMLParser(html)
    months: list[CertificateHistoryMonth] = []

    for row in tree.css("table tr")[1:]:
        cells = row.css("td")
        if len(cells) < 3:
            continue
        month_link = cells[0].css_first("a")
        month_url = month_link.attrs.get("href", "") if month_link else ""
        try:
            transferred_in = int(cells[1].text(strip=True).replace(",", ""))
        except ValueError:
            transferred_in = 0
        try:
            transferred_out = int(cells[2].text(strip=True).replace(",", ""))
        except ValueError:
            transferred_out = 0
        months.append(CertificateHistoryMonth(
            month=cells[0].text(strip=True),
            month_url=month_url,
            transferred_in=transferred_in,
            transferred_out=transferred_out,
        ))

    return CertificateHistory(organisation_id=organisation_id, cert_type=cert_type, months=months)

# endregion parsers
