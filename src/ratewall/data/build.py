"""Build source-backed snapshot bundles."""

from __future__ import annotations

import os
import signal
import socket
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from ratewall.data.demo import build_demo_snapshots, fallback_snapshot
from ratewall.data.snapshots import write_snapshot_bundle
from ratewall.sources.cbo import CboAdapter
from ratewall.sources.fed_feds import FedFedsAdapter
from ratewall.sources.fed_h41 import FedH41Adapter
from ratewall.sources.fed_dfa import FedDfaAdapter
from ratewall.sources.fiscaldata import FiscalDataAdapter
from ratewall.sources.fred import FredAdapter
from ratewall.sources.jec import JecTreasuryAdapter
from ratewall.sources.nyfed import NyFedAdapter
from ratewall.sources.ofr import OfrMmfAdapter
from ratewall.sources.registry import SourceRegistry
from ratewall.sources.sec_nmfp import SecNmfpAdapter
from ratewall.sources.sffed import SfFedAdapter
from ratewall.sources.tic import TicAdapter
from ratewall.sources.treasury_hqm import TreasuryHqmAdapter
from ratewall.sources.treasury_direct import TreasuryDirectBuybackAdapter


DEFAULT_LIVE_SERIES_TIMEOUT_SECONDS = 240
DEFAULT_LIVE_SOCKET_TIMEOUT_SECONDS = 30

DEFAULT_SERIES = (
    "WRESBAL",
    "RRPONTSYD",
    "GDP",
    "PCEC",
    "PCECC96",
    "DSPI",
    "FEDFUNDS",
    "IORB",
    "IOER",
    "PCEPILFE",
    "PII",
    "W055RC1",
    "NA000309Q",
    "NA000310Q",
    "TOTALSL",
    "REVOLSL",
    "NONREVSL",
    "TERMCBCCALLNS",
    "CREACBM027NBOG",
    "DRCRELEXFACBS",
    "MORTGAGE30US",
    "B112RC1Q027SBEA",
    "INDPRO",
    "UNRATE",
    "TDSP",
    "CDSP",
    "DRCCLACBS",
    "DRCLACBS",
    "BUSLOANS",
    "TOTLL",
    "DPSACBW027SBOG",
    "SNDR",
    "DTB3",
    "WTREGEN",
    "NFCI",
    "BAMLH0A0HYM2",
    "BAA",
    "TREASURY_HQM_EOM_10Y_PAR",
    "FDHBPIN",
    "FDHBFIN",
    "FDHBFRBN",
    "BOGZ1LM153061105Q",
    "BOGZ1FL763061100Q",
    "BOGZ1FL633061105Q",
    "BOGZ1FL653061105Q",
    "BOGZ1FL523061105Q",
    "BOGZ1FL573061105Q",
    "BOGZ1FU106130001Q",
    "BOGZ1FU106130101Q",
    "NCBCDCA",
    "TSDABSNNCB",
    "TSABSNNCB",
    "BOGZ1FL103034000Q",
    "SRPSABSNNCB",
    "CBLBSNNCB",
    "NCBDBIQ027S",
    "NCBLL",
    "CPLBSNNCB",
    "debt_to_penny",
    "treasury_dts",
    "mts_table_4",
    "treasury_mspd_table_3",
    "treasury_mspd_table_1",
    "treasury_buybacks",
    "treasury_auction_frn_terms",
    "treasury_auction_tips_terms",
    "treasury_frn_daily_indexes",
    "treasury_tips_cpi_detail",
    "tic_treasury_sector_transactions",
    "tic_foreign_treasury_stock_split",
    "ofr_mmf_treasury_holdings",
    "sec_nmfp_mmf_treasury_cusip_holdings",
    "cbo_budget_economic_outlook",
    "h41_current",
    "treasury_repricing_anchor",
    "distributional_interest_exposure",
    "fed_dfa_household_account_type_context",
    "fed_dfa_household_liability_context",
    "nyfed_soma_summary",
    "nyfed_sofr",
    "sf_fed_monetary_policy_surprises",
    "fed_brw_monetary_policy_shocks",
    "romer_romer_2004",
)


def build_snapshot_bundle(
    *,
    registry: SourceRegistry,
    output: Path,
    mode: str = "demo",
    series_ids: tuple[str, ...] = DEFAULT_SERIES,
    progress: bool = False,
) -> Path:
    if mode == "demo":
        snapshots = [
            snapshot
            for snapshot in build_demo_snapshots(registry)
            if snapshot.metadata.series_id in series_ids
        ]
        return write_snapshot_bundle(snapshots, output)
    if mode != "live":
        raise ValueError("mode must be 'demo' or 'live'")

    _configure_live_socket_timeout()
    series_timeout = _live_series_timeout_seconds()
    fred = FredAdapter(registry)
    fiscaldata = FiscalDataAdapter(registry)
    cbo = CboAdapter(registry)
    h41 = FedH41Adapter(registry)
    dfa = FedDfaAdapter(registry)
    nyfed = NyFedAdapter(registry)
    jec = JecTreasuryAdapter(registry)
    sffed = SfFedAdapter(registry)
    treasury_direct = TreasuryDirectBuybackAdapter(registry)
    treasury_hqm = TreasuryHqmAdapter(registry)
    tic = TicAdapter(registry)
    ofr = OfrMmfAdapter(registry)
    sec_nmfp = SecNmfpAdapter(registry)
    fed_feds = FedFedsAdapter(registry)
    snapshots = []
    for series_id in series_ids:
        spec = registry.series_definition(series_id)
        started = time.monotonic()
        _log_live_progress(
            (
                f"pulling {series_id} from {spec.source}; "
                f"endpoint={spec.endpoint}"
            ),
            enabled=progress,
        )
        try:
            with _live_series_deadline(series_id, series_timeout):
                snapshots.append(
                    _pull_live_series(
                        series_id=series_id,
                        source_id=spec.source,
                        fred=fred,
                        fiscaldata=fiscaldata,
                        treasury_direct=treasury_direct,
                        treasury_hqm=treasury_hqm,
                        tic=tic,
                        ofr=ofr,
                        sec_nmfp=sec_nmfp,
                        cbo=cbo,
                        h41=h41,
                        dfa=dfa,
                        nyfed=nyfed,
                        jec=jec,
                        sffed=sffed,
                        fed_feds=fed_feds,
                    )
                )
            _log_live_progress(
                f"completed {series_id} in {time.monotonic() - started:.1f}s",
                enabled=progress,
            )
        except Exception as exc:
            _log_live_progress(
                f"fallback {series_id} after {time.monotonic() - started:.1f}s: "
                f"{type(exc).__name__}: {exc}; endpoint={spec.endpoint}",
                enabled=progress,
            )
            snapshots.append(
                fallback_snapshot(
                    registry,
                    series_id,
                    reason=(
                        f"{type(exc).__name__}: {exc}; "
                        f"source={spec.source}; endpoint={spec.endpoint}"
                    ),
                )
            )
    return write_snapshot_bundle(snapshots, output)


def _pull_live_series(
    *,
    series_id: str,
    source_id: str,
    fred: FredAdapter,
    fiscaldata: FiscalDataAdapter,
    treasury_direct: TreasuryDirectBuybackAdapter,
    treasury_hqm: TreasuryHqmAdapter,
    tic: TicAdapter,
    ofr: OfrMmfAdapter,
    sec_nmfp: SecNmfpAdapter,
    cbo: CboAdapter,
    h41: FedH41Adapter,
    dfa: FedDfaAdapter,
    nyfed: NyFedAdapter,
    jec: JecTreasuryAdapter,
    sffed: SfFedAdapter,
    fed_feds: FedFedsAdapter,
):
    if source_id == "fred":
        return fred.pull_series(series_id)
    if source_id == "treasury_fiscaldata":
        if series_id == "treasury_mspd_table_3":
            snapshot = _pull_latest_mspd_table3_snapshot(fiscaldata)
        else:
            snapshot = fiscaldata.pull_table(
                series_id,
                params=_fiscaldata_params(series_id),
                paginate=_fiscaldata_paginate(series_id),
            )
        _validate_live_snapshot_shape(snapshot)
        return snapshot
    if source_id == "treasury_direct":
        return treasury_direct.pull_buybacks(series_id)
    if source_id == "treasury_hqm":
        return treasury_hqm.pull_series(series_id)
    if source_id == "treasury_tic":
        if series_id == "tic_foreign_treasury_stock_split":
            return tic.pull_foreign_treasury_stock_split(series_id)
        return tic.pull_treasury_sector_transactions(series_id)
    if source_id == "ofr_stfm":
        return ofr.pull_dataset(series_id)
    if source_id == "sec_nmfp":
        return sec_nmfp.pull_treasury_holdings(series_id)
    if source_id == "cbo":
        return cbo.pull_resource(series_id)
    if source_id == "fed_h41":
        return h41.pull_release(series_id)
    if source_id == "fed_dfa":
        return dfa.pull_distributional_exposure(series_id)
    if source_id == "ny_fed":
        return nyfed.pull_endpoint(series_id)
    if source_id == "jec_treasury":
        return jec.pull_anchor(series_id)
    if source_id == "sf_fed":
        return sffed.pull_surprises(series_id)
    if source_id == "fed_feds":
        return fed_feds.pull_brw_shocks(series_id)
    raise ValueError(f"no live adapter for source {source_id}")


def _configure_live_socket_timeout() -> None:
    timeout = _env_int(
        "RATEWALL_LIVE_SOCKET_TIMEOUT_SECONDS",
        DEFAULT_LIVE_SOCKET_TIMEOUT_SECONDS,
        minimum=1,
    )
    socket.setdefaulttimeout(timeout)


def _live_series_timeout_seconds() -> int:
    return _env_int(
        "RATEWALL_LIVE_SERIES_TIMEOUT_SECONDS",
        DEFAULT_LIVE_SERIES_TIMEOUT_SECONDS,
        minimum=0,
    )


def _env_int(name: str, default: int, *, minimum: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        parsed = int(raw)
    except ValueError:
        return default
    return max(minimum, parsed)


@contextmanager
def _live_series_deadline(series_id: str, seconds: int):
    if seconds <= 0 or not hasattr(signal, "SIGALRM"):
        yield
        return
    if threading.current_thread() is not threading.main_thread():
        yield
        return

    previous_handler = signal.getsignal(signal.SIGALRM)

    def _raise_timeout(_signum, _frame) -> None:
        raise TimeoutError(
            f"live retrieval exceeded {seconds}s for {series_id}; "
            "using provenance-preserving fallback"
        )

    signal.signal(signal.SIGALRM, _raise_timeout)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)


def _log_live_progress(message: str, *, enabled: bool = False) -> None:
    env_value = os.environ.get("RATEWALL_LIVE_PROGRESS", "").lower()
    env_enabled = env_value in {"1", "true", "yes"}
    env_disabled = env_value in {"0", "false", "no"}
    if env_disabled or not (enabled or env_enabled):
        return
    print(f"[ratewall-live] {message}", file=sys.stderr, flush=True)


def _fiscaldata_params(series_id: str) -> dict[str, str]:
    if series_id == "debt_to_penny":
        return {
            "filter": "record_date:gte:2012-01-01",
            "page[size]": "10000",
            "sort": "-record_date",
        }
    if series_id == "mts_table_4":
        return {
            "filter": "record_date:gte:2026-01-01",
            "page[size]": "1000",
            "sort": "-record_date",
        }
    if series_id == "treasury_dts":
        return {
            "filter": "record_date:gte:2026-01-01",
            "fields": (
                "record_date,account_type,open_today_bal,open_month_bal,"
                "open_fiscal_year_bal,close_today_bal,table_nbr,table_nm,"
                "sub_table_name,src_line_nbr,record_fiscal_year,"
                "record_fiscal_quarter,record_calendar_year,"
                "record_calendar_quarter,record_calendar_month,"
                "record_calendar_day"
            ),
            "page[size]": "5000",
            "sort": "-record_date,src_line_nbr",
        }
    if series_id == "treasury_mspd_table_3":
        return {
            "filter": "record_date:gte:2012-01-01",
            "fields": (
                "record_date,security_type_desc,series_cd,"
                "security_class1_desc,security_class2_desc,security_class3_desc,"
                "interest_rate_pct,yield_pct,issue_date,maturity_date,"
                "interest_pay_date_1,interest_pay_date_2,interest_pay_date_3,"
                "interest_pay_date_4,issued_amt,inflation_adj_amt,redeemed_amt,"
                "outstanding_amt,prior_month_outstanding_amt,"
                "current_month_issued_amt,current_month_redeemed_amt,"
                "current_month_outstanding_amt,src_line_nbr,record_calendar_year,"
                "record_calendar_quarter,record_calendar_month"
            ),
            "page[size]": "10000",
            "sort": "-record_date",
        }
    if series_id == "treasury_mspd_table_1":
        return {
            "filter": "record_date:gte:2012-01-01",
            "page[size]": "10000",
            "sort": "-record_date",
        }
    if series_id == "treasury_auction_frn_terms":
        return {
            "filter": "floating_rate:eq:Yes,record_date:gte:2024-01-01",
            "page[size]": "5000",
            "sort": "-auction_date",
        }
    if series_id == "treasury_auction_tips_terms":
        return {
            "filter": "inflation_index_security:eq:Yes,record_date:gte:1997-01-01",
            "page[size]": "5000",
            "sort": "-auction_date",
        }
    if series_id == "treasury_frn_daily_indexes":
        return {
            "filter": "record_date:gte:2024-01-01",
            "page[size]": "10000",
            "sort": "-record_date",
        }
    if series_id == "treasury_tips_cpi_detail":
        return {
            "filter": "index_date:gte:2024-01-01",
            "page[size]": "10000",
            "sort": "-index_date",
        }
    return {"page[size]": "5000"}


def _pull_latest_mspd_table3_snapshot(
    fiscaldata: FiscalDataAdapter,
):
    """Fetch the latest official MSPD Table 3 month without full-history paging."""

    latest_date_snapshot = fiscaldata.pull_table(
        "treasury_mspd_table_3",
        params={
            "fields": "record_date",
            "page[size]": "1",
            "sort": "-record_date",
        },
        paginate=False,
    )
    if not latest_date_snapshot.records:
        raise ValueError("MSPD table 3 latest-date query returned no records")
    latest_record = latest_date_snapshot.records[0]
    latest_date = str(latest_record.get("record_date") or "")
    if not latest_date:
        raise ValueError("MSPD table 3 latest-date query lacked record_date")

    params = dict(_fiscaldata_params("treasury_mspd_table_3"))
    params["filter"] = f"record_date:eq:{latest_date}"
    params["sort"] = "src_line_nbr"
    return fiscaldata.pull_table(
        "treasury_mspd_table_3",
        params=params,
        paginate=False,
    )


def _fiscaldata_paginate(series_id: str) -> bool:
    return series_id in {
        "debt_to_penny",
        "treasury_mspd_table_3",
        "treasury_mspd_table_1",
        "treasury_tips_cpi_detail",
    }


def _validate_live_snapshot_shape(snapshot) -> None:
    if snapshot.metadata.series_id == "mts_table_4":
        fields = {
            "current_fytd_net_outly_amt",
            "current_fytd_net_outlay_amt",
            "amount",
        }
        if not any(fields & set(record.keys()) for record in snapshot.records):
            raise ValueError(
                "MTS table response lacks a net-interest outlay field used by "
                "the accounting input normalizer"
            )
    if snapshot.metadata.series_id == "treasury_mspd_table_3":
        fields = {"record_date", "maturity_date", "security_class1_desc"}
        if not snapshot.records or not fields <= set(snapshot.records[0].keys()):
            raise ValueError(
                "MSPD table 3 response lacks maturity fields used by the "
                "repricing ladder normalizer"
            )
    if snapshot.metadata.series_id == "treasury_mspd_table_1":
        fields = {"record_date", "security_type_desc", "debt_held_public_mil_amt"}
        if not snapshot.records or not fields <= set(snapshot.records[0].keys()):
            raise ValueError(
                "MSPD table 1 response lacks debt class fields used by the "
                "reconciliation table"
            )
    if snapshot.metadata.series_id == "treasury_dts":
        fields = {"record_date", "account_type", "open_today_bal", "table_nm"}
        if not snapshot.records or not fields <= set(snapshot.records[0].keys()):
            raise ValueError(
                "DTS operating cash balance response lacks TGA fields used by "
                "the public-finance timing source gate"
            )
