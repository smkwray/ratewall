#!/usr/bin/env python3
"""Materialize fail-closed conventional-drag source review surfaces.

This script acquires review-only source artifacts, hashes whatever is locally
available, and emits two backend inputs:

* a conventional-drag research-parameterization source frontier; and
* a policy-path contract-interval review joined to the SF Fed candidate vector.

It deliberately does not compute bps-year exposure, GDP-share drag, denominator
priors, or runtime outputs.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
RESEARCH_RAW_DIR = ROOT / "data/raw/conventional_drag_parameterization_sources"
CONTRACT_RAW_DIR = ROOT / "data/raw/policy_path_contract_interval_sources"
POLICY_PATH_RAW_DIR = ROOT / "data/raw/policy_path_protocol_sources"
FRONTIER_CSV = (
    RESEARCH_RAW_DIR
    / "conventional_drag_research_parameterization_source_frontier.csv"
)
FRONTIER_MANIFEST = RESEARCH_RAW_DIR / "source_acquisition_manifest.json"
CONTRACT_REVIEW_CSV = CONTRACT_RAW_DIR / "policy_path_contract_interval_source_review.csv"
CONTRACT_MANIFEST = CONTRACT_RAW_DIR / "contract_interval_source_acquisition_manifest.json"
CONTRACT_BLOCKER_CSV = CONTRACT_RAW_DIR / "policy_path_contract_spec_acquisition_blocker.csv"
FRBUS_READINESS_CSV = RESEARCH_RAW_DIR / "frbus_model_benchmark_simulation_readiness.csv"
OPENICPSR_REPLICATION_PACKAGE_MANIFEST_CSV = (
    RESEARCH_RAW_DIR / "openicpsr_replication_package_source_manifest.csv"
)
OPENICPSR_REPLICATION_PACKAGE_ACQUISITION_MANIFEST = (
    RESEARCH_RAW_DIR / "openicpsr_replication_package_acquisition_manifest.json"
)
CANDIDATE_VECTOR_CSV = (
    POLICY_PATH_RAW_DIR / "sf_fed_monetary_policy_surprises_candidate_event_vector.csv"
)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "RateWall-source-review/1.0 "
    "(backend fail-closed research artifact acquisition)"
)
REQUEST_TIMEOUT_SECONDS = 15

FORBIDDEN_SWITCHES = [
    "denominator_prior_update_allowed",
    "empirical_threshold_claim_enabled",
    "enters_main_ratio",
    "evidence_mode_enabled",
    "canonical_ratio_entry",
    "prior_narrowing_allowed",
    "split_denominator_promotion_allowed",
    "formula_replacement_allowed",
    "main_offset_ratio_changed_this_tranche",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "mpc_channel_enabled",
    "holder_allocation_enabled",
    "reset_calendar_construction_enabled",
    "reset_calendar_enabled",
    "raw_rate_shock_enabled",
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "causal_financialization_claim_enabled",
]

REQUIRED_CONTRACT_FIELDS = [
    (
        "point_estimate_gdp_share_per_100bp_year",
        "blocked_no_source_point_estimate",
        "Locate a source-reported current-demand response normalized to "
        "GDP-share per 100bp-year, or keep the route blocked.",
    ),
    (
        "uncertainty_interval",
        "blocked_no_source_uncertainty_interval",
        "Extract a source-reported standard error, confidence interval, or "
        "replication uncertainty surface for the mapped parameter.",
    ),
    (
        "policy_path_normalization",
        "blocked_no_compatible_policy_path_normalization",
        "Review whether the source shock maps to an admitted 100bp-year policy "
        "path or another explicitly normalized policy-path measure.",
    ),
    (
        "current_demand_mapping",
        "blocked_no_current_demand_mapping",
        "Identify demand-side GDP, PCE, investment, or current-demand component "
        "responses rather than generic financial-outcome diagnostics.",
    ),
    (
        "gdp_share_conversion",
        "blocked_no_gdp_share_conversion",
        "Record a source-backed conversion from reported units into GDP-share "
        "units before any denominator use.",
    ),
    (
        "replication_or_aggregation",
        "blocked_no_independent_replication_or_aggregation",
        "Replicate the reported response or aggregate source-reported IRFs "
        "within a declared tolerance.",
    ),
    (
        "robustness_transport",
        "blocked_no_robustness_transport_review",
        "Review shock-family, sample, horizon, information-effect, and "
        "transport limits before parameterization.",
    ),
    (
        "provenance_and_promotion_rule",
        "blocked_no_provenance_promotion_rule",
        "Hash source artifacts and define a separate promotion rule; acquiring "
        "metadata alone cannot narrow priors.",
    ),
]


@dataclass(frozen=True)
class ArtifactTarget:
    source_candidate_handle: str
    source_family: str
    artifact_handle: str
    urls: tuple[str, ...]
    local_name: str
    source_type: str
    replication_package_available: str
    parser_hint: str
    shock_definition_text: str
    source_url_or_citation_handle: str


@dataclass(frozen=True)
class OpenICPSRTarget:
    source_candidate_handle: str
    project_id: str
    version_id: str
    package_object_handle: str
    package_object_path: str
    object_kind: str
    expected_file_type: str
    expected_size_label: str
    candidate_review_role: str
    urls: tuple[str, ...]
    local_name: str
    source_url_or_citation_handle: str


RESEARCH_ARTIFACT_TARGETS = [
    ArtifactTarget(
        source_candidate_handle="frbus_python_model",
        source_family="official_model_benchmark",
        artifact_handle="frbus_python_landing_page_html",
        urls=("https://www.federalreserve.gov/econres/us-models-python.htm",),
        local_name="frbus_python_landing_page.html",
        source_type="official_model_page",
        replication_package_available="model_code_package_public",
        parser_hint="html_links_and_text_only",
        shock_definition_text="official model benchmark; no empirical shock admitted",
        source_url_or_citation_handle="federal_reserve_frbus_python",
    ),
    ArtifactTarget(
        source_candidate_handle="frbus_python_model",
        source_family="official_model_benchmark",
        artifact_handle="frbus_python_package_zip",
        urls=("https://www.federalreserve.gov/econres/files/pyfrbus.zip",),
        local_name="pyfrbus.zip",
        source_type="official_model_code_package",
        replication_package_available="model_code_package_public",
        parser_hint="zip_manifest_only",
        shock_definition_text=(
            "official FRB/US model code benchmark; model simulation is not an "
            "empirical denominator calibration"
        ),
        source_url_or_citation_handle="federal_reserve_frbus_python_zip",
    ),
    ArtifactTarget(
        source_candidate_handle="frbus_python_model",
        source_family="official_model_benchmark",
        artifact_handle="frbus_data_only_package_zip",
        urls=("https://www.federalreserve.gov/econres/files/data_only_package.zip",),
        local_name="data_only_package.zip",
        source_type="official_model_data_package",
        replication_package_available="model_data_package_public",
        parser_hint="zip_manifest_only",
        shock_definition_text=(
            "official FRB/US data package benchmark; illustrative model data "
            "do not admit an empirical denominator parameter"
        ),
        source_url_or_citation_handle="federal_reserve_frbus_data_package",
    ),
    ArtifactTarget(
        source_candidate_handle="miranda_agrippino_ricco_aej",
        source_family="empirical_replication_candidate",
        artifact_handle="openicpsr_e116841_project_page_html",
        urls=("https://www.openicpsr.org/openicpsr/project/116841/version/V1/view",),
        local_name="openicpsr_e116841_project_page.html",
        source_type="replication_package_project_page",
        replication_package_available="public_replication_package_project_page",
        parser_hint="project_metadata_and_download_links_only",
        shock_definition_text=(
            "monetary-policy transmission with information-effect controls; "
            "normalization not admitted as 100bp-year"
        ),
        source_url_or_citation_handle="openicpsr_e116841_miranda_agrippino_ricco",
    ),
    ArtifactTarget(
        source_candidate_handle="gertler_karadi_aej",
        source_family="empirical_replication_candidate",
        artifact_handle="openicpsr_e114082_project_page_html",
        urls=("https://www.openicpsr.org/openicpsr/project/114082/version/V1/view",),
        local_name="openicpsr_e114082_project_page.html",
        source_type="replication_package_project_page",
        replication_package_available="public_replication_package_project_page",
        parser_hint="project_metadata_and_download_links_only",
        shock_definition_text=(
            "external-instrument monetary-policy shocks; not an admitted "
            "bps-year policy-path measure"
        ),
        source_url_or_citation_handle="openicpsr_e114082_gertler_karadi",
    ),
    ArtifactTarget(
        source_candidate_handle="sf_fed_bauer_swanson_mps_usmpd",
        source_family="policy_shock_replication_context",
        artifact_handle="sf_fed_monetary_policy_surprises_page_html",
        urls=(
            "https://www.frbsf.org/research-and-insights/data-and-indicators/"
            "monetary-policy-surprises/",
        ),
        local_name="sf_fed_monetary_policy_surprises_page.html",
        source_type="policy_shock_source_page",
        replication_package_available="source_workbook_and_code_context_available",
        parser_hint="html_context_only_existing_workbook_zip_reused",
        shock_definition_text=(
            "high-frequency FOMC-window futures surprises; scalar/candidate "
            "vectors remain blocked for bps-year use"
        ),
        source_url_or_citation_handle="sf_fed_monetary_policy_surprises",
    ),
    ArtifactTarget(
        source_candidate_handle="nakamura_steinsson_policy_news",
        source_family="policy_news_context",
        artifact_handle="macro_policy_lab_policy_news_page_html",
        urls=(
            "https://www.macropolicylab.org/research/"
            "lonsthc06vtm6wu99vsz7jpjg52hv2",
        ),
        local_name="macro_policy_lab_policy_news_page.html",
        source_type="policy_news_context_page",
        replication_package_available="context_page_public",
        parser_hint="html_context_only",
        shock_definition_text=(
            "policy-news and information-effect context; no RateWall bps-year "
            "or GDP-share denominator admitted"
        ),
        source_url_or_citation_handle="nakamura_steinsson_policy_news_context",
    ),
    ArtifactTarget(
        source_candidate_handle="brw_feds_data_or_methods_context",
        source_family="shock_robustness_context",
        artifact_handle="fed_data_or_methods_page_html",
        urls=(
            "https://www.federalreserve.gov/econres/feds/"
            "monetary-policy-shocks-data-or-methods.htm",
        ),
        local_name="fed_monetary_policy_shocks_data_or_methods.html",
        source_type="shock_method_comparison_page",
        replication_package_available="context_page_public",
        parser_hint="html_context_only",
        shock_definition_text=(
            "shock-series comparison and robustness context; scalar shocks not "
            "admitted as bps-year paths"
        ),
        source_url_or_citation_handle="fed_data_or_methods_monetary_policy_shocks",
    ),
    ArtifactTarget(
        source_candidate_handle="bea_fred_conversion_context",
        source_family="conversion_context",
        artifact_handle="fred_tdsp_page_html",
        urls=("https://fred.stlouisfed.org/series/TDSP",),
        local_name="fred_tdsp_page.html",
        source_type="financial_ratio_context_page",
        replication_package_available="public_series_context",
        parser_hint="html_context_only",
        shock_definition_text=(
            "TDSP financial-burden ratio context; not current-demand GDP-share "
            "drag evidence"
        ),
        source_url_or_citation_handle="fred_tdsp",
    ),
]

OPENICPSR_OBJECT_TARGETS = [
    OpenICPSRTarget(
        source_candidate_handle="miranda_agrippino_ricco_aej",
        project_id="116841",
        version_id="V1",
        package_object_handle="project_page",
        package_object_path="/openicpsr/116841/fcr:versions/V1",
        object_kind="project_page_html",
        expected_file_type="text/html",
        expected_size_label="",
        candidate_review_role="project_metadata",
        urls=("https://www.openicpsr.org/openicpsr/project/116841/version/V1/view",),
        local_name="openicpsr_e116841_project_page.html",
        source_url_or_citation_handle="openicpsr_e116841_miranda_agrippino_ricco",
    ),
    OpenICPSRTarget(
        source_candidate_handle="miranda_agrippino_ricco_aej",
        project_id="116841",
        version_id="V1",
        package_object_handle="oai_dc_metadata",
        package_object_path="oai_dc:116841:V1",
        object_kind="oai_metadata_xml",
        expected_file_type="application/xml",
        expected_size_label="",
        candidate_review_role="project_metadata",
        urls=(
            "https://pcms.icpsr.umich.edu/pcms/api/1.0/oai/studies?"
            "metadataPrefix=oai_dc&verb=GetRecord&identifier=116841&"
            "version=V1&page=/openicpsr/project/116841/version/V1/view?flag=follow",
        ),
        local_name="e116841_dc.xml",
        source_url_or_citation_handle="openicpsr_e116841_oai_dc",
    ),
    OpenICPSRTarget(
        source_candidate_handle="miranda_agrippino_ricco_aej",
        project_id="116841",
        version_id="V1",
        package_object_handle="oai_ddi25_metadata",
        package_object_path="oai_ddi25:116841:V1",
        object_kind="oai_metadata_xml",
        expected_file_type="application/xml",
        expected_size_label="",
        candidate_review_role="project_metadata",
        urls=(
            "https://pcms.icpsr.umich.edu/pcms/api/1.0/oai/studies?"
            "metadataPrefix=oai_ddi25&verb=GetRecord&identifier=116841&"
            "version=V1&page=/openicpsr/project/116841/version/V1/view?flag=follow",
        ),
        local_name="e116841_ddi25.xml",
        source_url_or_citation_handle="openicpsr_e116841_oai_ddi25",
    ),
    OpenICPSRTarget(
        source_candidate_handle="miranda_agrippino_ricco_aej",
        project_id="116841",
        version_id="V1",
        package_object_handle="replication_public_folder_page",
        package_object_path="/openicpsr/116841/fcr:versions/V1/REPLICATION-FILES---PUBLIC",
        object_kind="folder_page_html",
        expected_file_type="text/html",
        expected_size_label="",
        candidate_review_role="folder_inventory",
        urls=(
            "https://www.openicpsr.org/openicpsr/project/116841/version/V1/view?"
            "flag=follow&pageSelected=0&pageSize=100&path=%2Fopenicpsr%2F116841"
            "%2Ffcr%3Aversions%2FV1%2FREPLICATION-FILES---PUBLIC&"
            "sortAsc=true&sortOrder=%28%3Ftitle%29&type=folder",
        ),
        local_name="e116841_replication_public_folder_page.html",
        source_url_or_citation_handle="openicpsr_e116841_replication_public_folder",
    ),
    OpenICPSRTarget(
        source_candidate_handle="miranda_agrippino_ricco_aej",
        project_id="116841",
        version_id="V1",
        package_object_handle="readme_pdf_file_page",
        package_object_path="/openicpsr/116841/fcr:versions/V1/REPLICATION-FILES---PUBLIC/README.pdf",
        object_kind="file_page_html",
        expected_file_type="application/pdf",
        expected_size_label="42.1 KB",
        candidate_review_role="readme",
        urls=(
            "https://www.openicpsr.org/openicpsr/project/116841/version/V1/view?"
            "path=%2Fopenicpsr%2F116841%2Ffcr%3Aversions%2FV1%2F"
            "REPLICATION-FILES---PUBLIC%2FREADME.pdf&type=file",
        ),
        local_name="e116841_readme_file_page.html",
        source_url_or_citation_handle="openicpsr_e116841_readme_pdf",
    ),
    OpenICPSRTarget(
        source_candidate_handle="miranda_agrippino_ricco_aej",
        project_id="116841",
        version_id="V1",
        package_object_handle="alldata_xlsx_file_page",
        package_object_path=(
            "/openicpsr/116841/fcr:versions/V1/REPLICATION-FILES---PUBLIC/DATA/"
            "Miranda-Agrippino&Ricco_ALLDATA.xlsx"
        ),
        object_kind="file_page_html",
        expected_file_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        expected_size_label="857.8 KB",
        candidate_review_role="data_workbook_inventory",
        urls=(
            "https://www.openicpsr.org/openicpsr/project/116841/version/V1/view?"
            "path=%2Fopenicpsr%2F116841%2Ffcr%3Aversions%2FV1%2F"
            "REPLICATION-FILES---PUBLIC%2FDATA%2FMiranda-Agrippino%2526"
            "Ricco_ALLDATA.xlsx&type=file",
        ),
        local_name="e116841_alldata_file_page.html",
        source_url_or_citation_handle="openicpsr_e116841_alldata_xlsx",
    ),
    OpenICPSRTarget(
        source_candidate_handle="miranda_agrippino_ricco_aej",
        project_id="116841",
        version_id="V1",
        package_object_handle="build_data_m_file_page",
        package_object_path="/openicpsr/116841/fcr:versions/V1/REPLICATION-FILES---PUBLIC/DATA/BUILD_data.m",
        object_kind="file_page_html",
        expected_file_type="text/x-objcsrc",
        expected_size_label="3.7 KB",
        candidate_review_role="data_build_code_inventory",
        urls=(
            "https://www.openicpsr.org/openicpsr/project/116841/version/V1/view?"
            "path=%2Fopenicpsr%2F116841%2Ffcr%3Aversions%2FV1%2F"
            "REPLICATION-FILES---PUBLIC%2FDATA%2FBUILD_data.m&type=file",
        ),
        local_name="e116841_build_data_file_page.html",
        source_url_or_citation_handle="openicpsr_e116841_build_data_m",
    ),
    OpenICPSRTarget(
        source_candidate_handle="miranda_agrippino_ricco_aej",
        project_id="116841",
        version_id="V1",
        package_object_handle="replicate_figure10_m_file_page",
        package_object_path="/openicpsr/116841/fcr:versions/V1/REPLICATION-FILES---PUBLIC/Replicate_Figure10.m",
        object_kind="file_page_html",
        expected_file_type="text/x-objcsrc",
        expected_size_label="11.1 KB",
        candidate_review_role="irf_figure_code_inventory",
        urls=(
            "https://www.openicpsr.org/openicpsr/project/116841/version/V1/view?"
            "path=%2Fopenicpsr%2F116841%2Ffcr%3Aversions%2FV1%2F"
            "REPLICATION-FILES---PUBLIC%2FReplicate_Figure10.m&type=file",
        ),
        local_name="e116841_replicate_figure10_file_page.html",
        source_url_or_citation_handle="openicpsr_e116841_replicate_figure10_m",
    ),
    OpenICPSRTarget(
        source_candidate_handle="gertler_karadi_aej",
        project_id="114082",
        version_id="V1",
        package_object_handle="project_page",
        package_object_path="/openicpsr/114082/fcr:versions/V1",
        object_kind="project_page_html",
        expected_file_type="text/html",
        expected_size_label="",
        candidate_review_role="project_metadata",
        urls=("https://www.openicpsr.org/openicpsr/project/114082/version/V1/view",),
        local_name="openicpsr_e114082_project_page.html",
        source_url_or_citation_handle="openicpsr_e114082_gertler_karadi",
    ),
    OpenICPSRTarget(
        source_candidate_handle="gertler_karadi_aej",
        project_id="114082",
        version_id="V1",
        package_object_handle="oai_dc_metadata",
        package_object_path="oai_dc:114082:V1",
        object_kind="oai_metadata_xml",
        expected_file_type="application/xml",
        expected_size_label="",
        candidate_review_role="project_metadata",
        urls=(
            "https://pcms.icpsr.umich.edu/pcms/api/1.0/oai/studies?"
            "metadataPrefix=oai_dc&verb=GetRecord&identifier=114082&"
            "version=V1&page=/openicpsr/project/114082/version/V1/view?flag=follow",
        ),
        local_name="e114082_dc.xml",
        source_url_or_citation_handle="openicpsr_e114082_oai_dc",
    ),
    OpenICPSRTarget(
        source_candidate_handle="gertler_karadi_aej",
        project_id="114082",
        version_id="V1",
        package_object_handle="oai_ddi25_metadata",
        package_object_path="oai_ddi25:114082:V1",
        object_kind="oai_metadata_xml",
        expected_file_type="application/xml",
        expected_size_label="",
        candidate_review_role="project_metadata",
        urls=(
            "https://pcms.icpsr.umich.edu/pcms/api/1.0/oai/studies?"
            "metadataPrefix=oai_ddi25&verb=GetRecord&identifier=114082&"
            "version=V1&page=/openicpsr/project/114082/version/V1/view?flag=follow",
        ),
        local_name="e114082_ddi25.xml",
        source_url_or_citation_handle="openicpsr_e114082_oai_ddi25",
    ),
    OpenICPSRTarget(
        source_candidate_handle="gertler_karadi_aej",
        project_id="114082",
        version_id="V1",
        package_object_handle="code_folder_page",
        package_object_path="/openicpsr/114082/fcr:versions/V1/ReprFiles_GK_2013-0329/code",
        object_kind="folder_page_html",
        expected_file_type="text/html",
        expected_size_label="20 records",
        candidate_review_role="code_inventory",
        urls=(
            "https://www.openicpsr.org/openicpsr/project/114082/version/V1/view?"
            "flag=follow&pageSelected=0&pageSize=100&path=%2Fopenicpsr%2F114082"
            "%2Ffcr%3Aversions%2FV1%2FReprFiles_GK_2013-0329%2Fcode&"
            "sortAsc=true&sortOrder=%28%3Ftitle%29&type=folder",
        ),
        local_name="e114082_code_folder_page.html",
        source_url_or_citation_handle="openicpsr_e114082_code_folder",
    ),
    OpenICPSRTarget(
        source_candidate_handle="gertler_karadi_aej",
        project_id="114082",
        version_id="V1",
        package_object_handle="readme_pdf_file_page",
        package_object_path="/openicpsr/114082/fcr:versions/V1/ReprFiles_GK_2013-0329/Readme.pdf",
        object_kind="file_page_html",
        expected_file_type="application/pdf",
        expected_size_label="44.1 KB",
        candidate_review_role="readme",
        urls=(
            "https://www.openicpsr.org/openicpsr/project/114082/version/V1/view?"
            "path=%2Fopenicpsr%2F114082%2Ffcr%3Aversions%2FV1%2F"
            "ReprFiles_GK_2013-0329%2FReadme.pdf&type=file",
        ),
        local_name="e114082_readme_file_page.html",
        source_url_or_citation_handle="openicpsr_e114082_readme_pdf",
    ),
    OpenICPSRTarget(
        source_candidate_handle="gertler_karadi_aej",
        project_id="114082",
        version_id="V1",
        package_object_handle="var_main_runme_file_page",
        package_object_path="/openicpsr/114082/fcr:versions/V1/ReprFiles_GK_2013-0329/code/VAR_main_RunMe.m",
        object_kind="file_page_html",
        expected_file_type="text/plain",
        expected_size_label="23.9 KB",
        candidate_review_role="proxy_svar_code_inventory",
        urls=(
            "https://www.openicpsr.org/openicpsr/project/114082/version/V1/view?"
            "path=%2Fopenicpsr%2F114082%2Ffcr%3Aversions%2FV1%2F"
            "ReprFiles_GK_2013-0329%2Fcode%2FVAR_main_RunMe.m&type=file",
        ),
        local_name="e114082_var_main_runme_file_page.html",
        source_url_or_citation_handle="openicpsr_e114082_var_main_runme_m",
    ),
]

CONTRACT_SPEC_TARGETS = [
    ArtifactTarget(
        source_candidate_handle="cme_30_day_fed_funds_futures",
        source_family="official_contract_spec",
        artifact_handle="cme_cbot_chapter_22_fed_funds_pdf",
        urls=(
            "https://www.cmegroup.com/rulebook/CBOT/III/22.pdf"
            "?redirect=%2Frulebook%2FCBOT%2FV%2F22%2F22.pdf",
            "https://www.cmegroup.com/rulebook/CBOT/III/22.pdf",
        ),
        local_name="cme_cbot_chapter_22_30_day_fed_funds_futures.pdf",
        source_type="contract_rulebook_pdf",
        replication_package_available="not_applicable_contract_spec",
        parser_hint="hash_and_rule_label_only",
        shock_definition_text=(
            "30-day federal funds futures quote/reference-month contract rule"
        ),
        source_url_or_citation_handle="cme_cbot_chapter_22_fed_funds",
    ),
    ArtifactTarget(
        source_candidate_handle="cme_three_month_sofr_futures",
        source_family="official_contract_spec",
        artifact_handle="cme_chapter_460_sofr_pdf",
        urls=(
            "https://www.cmegroup.com/content/dam/cmegroup/rulebook/CME/IV/400/460.pdf",
            "https://www.cmegroup.com/rulebook/CME/III/460.pdf",
        ),
        local_name="cme_chapter_460_three_month_sofr_futures.pdf",
        source_type="contract_rulebook_pdf",
        replication_package_available="not_applicable_contract_spec",
        parser_hint="hash_and_rule_label_only",
        shock_definition_text="three-month SOFR futures reference-quarter contract rule",
        source_url_or_citation_handle="cme_chapter_460_sofr",
    ),
    ArtifactTarget(
        source_candidate_handle="cme_eurodollar_futures",
        source_family="official_contract_spec",
        artifact_handle="cme_eurodollar_futures_foundational_concepts_pdf",
        urls=(
            "https://www.cmegroup.com/education/files/"
            "eurodollar-futures-foundational-concepts.pdf",
            "https://www.cmegroup.com/trading/interest-rates/files/"
            "eurodollar-futures-foundational-concepts.pdf",
        ),
        local_name="cme_eurodollar_futures_foundational_concepts.pdf",
        source_type="contract_concepts_pdf",
        replication_package_available="not_applicable_contract_spec",
        parser_hint="hash_and_rule_label_only",
        shock_definition_text="Eurodollar futures quote and delivery-month context",
        source_url_or_citation_handle="cme_eurodollar_futures_foundational_concepts",
    ),
    ArtifactTarget(
        source_candidate_handle="fed_sofr_continuity",
        source_family="policy_path_continuity_context",
        artifact_handle="fed_sofr_continuity_paper_html",
        urls=(
            "https://www.federalreserve.gov/econres/feds/"
            "constructing-high-frequency-monetary-policy-surprises-from-sofr-"
            "futures.htm",
        ),
        local_name="fed_sofr_continuity_paper.html",
        source_type="fed_method_context_page",
        replication_package_available="accessible_materials_context",
        parser_hint="html_context_only",
        shock_definition_text=(
            "SOFR futures continuity context after Eurodollar transition; "
            "not an admitted RateWall bps-year integration formula"
        ),
        source_url_or_citation_handle="fed_sofr_continuity_note",
    ),
]

FRONTIER_FIELDS = [
    "frontier_row_id",
    "source_candidate_handle",
    "source_family",
    "artifact_handle",
    "artifact_path",
    "artifact_sha256",
    "artifact_size_bytes",
    "source_url_or_citation_handle",
    "source_type",
    "replication_package_available",
    "parser_status",
    "parsed_variable_or_file",
    "required_contract_field",
    "shock_definition_text",
    "shock_unit_status",
    "policy_path_exposure_definition_status",
    "current_demand_mapping_status",
    "gdp_share_conversion_status",
    "uncertainty_interval_status",
    "replication_status",
    "robustness_transport_status",
    "provenance_status",
    "research_parameterization_admission_status",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "exact_blocker",
    "next_backend_action",
    *FORBIDDEN_SWITCHES,
    "claim_boundary",
]

CONTRACT_REVIEW_FIELDS = [
    "contract_review_row_id",
    "candidate_vector_row_id",
    "source_sheet_vintage",
    "source_sheet_name",
    "event_id",
    "event_date",
    "event_time",
    "candidate_instrument_code",
    "source_cell_value_text",
    "source_cell_value_numeric",
    "literal_na_status",
    "instrument_family",
    "official_spec_source_handle",
    "official_spec_artifact_path",
    "official_spec_artifact_sha256",
    "official_spec_acquisition_status",
    "price_quote_rule",
    "rate_to_price_sign_status",
    "source_unit_status",
    "candidate_delivery_month",
    "delivery_month_selection_rule_status",
    "reference_period_start",
    "reference_period_end",
    "reference_period_year_fraction",
    "event_overlap_days",
    "event_overlap_year_fraction",
    "candidate_interval_weight_status",
    "policy_rate_bps_exposure",
    "bps_year_component",
    "bps_year_exposure_output",
    "candidate_gdp_share_drag_per_100bp_year",
    "bps_year_integration_status",
    "independent_replication_status",
    "protocol_admission_status",
    "source_admission_status",
    "exact_blocker",
    "next_backend_action",
    *FORBIDDEN_SWITCHES,
    "claim_boundary",
]

CONTRACT_BLOCKER_FIELDS = [
    "blocker_row_id",
    "official_spec_source_handle",
    "artifact_handle",
    "requested_urls",
    "local_artifact_path",
    "local_artifact_sha256",
    "acquisition_status",
    "attempts",
    "affected_candidate_instrument_codes",
    "covered_candidate_row_count",
    "fallback_path_status",
    "exact_blocker",
    "next_backend_action",
    *FORBIDDEN_SWITCHES,
    "claim_boundary",
]

FRBUS_READINESS_FIELDS = [
    "readiness_row_id",
    "source_candidate_handle",
    "artifact_handle",
    "artifact_path",
    "artifact_sha256",
    "artifact_size_bytes",
    "zip_entry_count",
    "readiness_field",
    "candidate_file_or_variable",
    "candidate_file_sha256",
    "file_manifest_status",
    "policy_shock_hook_candidate_status",
    "gdp_outcome_candidate_status",
    "pce_outcome_candidate_status",
    "investment_outcome_candidate_status",
    "shock_normalization_status",
    "gdp_share_conversion_status",
    "uncertainty_interval_status",
    "replication_status",
    "promotion_status",
    "model_benchmark_admission_status",
    "candidate_gdp_share_drag_per_100bp_year",
    "bps_year_exposure_output",
    "exact_blocker",
    "next_backend_action",
    *FORBIDDEN_SWITCHES,
    "claim_boundary",
]

OPENICPSR_REPLICATION_PACKAGE_MANIFEST_FIELDS = [
    "manifest_row_id",
    "source_candidate_handle",
    "project_id",
    "version_id",
    "package_object_handle",
    "package_object_path",
    "object_kind",
    "expected_file_type",
    "expected_size_label",
    "candidate_review_role",
    "source_url_or_citation_handle",
    "metadata_artifact_path",
    "metadata_artifact_sha256",
    "metadata_artifact_size_bytes",
    "metadata_acquisition_status",
    "download_attempt_status",
    "download_attempts",
    "parsed_title_or_name",
    "parsed_file_type",
    "parsed_size_label",
    "parsed_last_modified",
    "parsed_child_objects",
    "parsed_file_manifest_entry_count",
    "parsed_code_entry_count",
    "parsed_data_entry_count",
    "parsed_readme_entry_count",
    "parsed_candidate_file_names",
    "candidate_variable_or_irf_names",
    "candidate_variable_or_file_inventory",
    "source_file_payload_path",
    "source_file_payload_sha256",
    "source_file_payload_size_bytes",
    "source_file_payload_status",
    "source_file_payload_download_url",
    "source_file_payload_final_url",
    "source_file_payload_http_status",
    "source_file_payload_blocker_class",
    "source_file_payload_attempts",
    "candidate_variable_inventory_status",
    "candidate_irf_availability_status",
    "candidate_uncertainty_availability_status",
    "candidate_readme_status",
    "candidate_code_status",
    "candidate_data_status",
    "shock_definition_status",
    "shock_normalization_status",
    "policy_path_exposure_definition_status",
    "current_demand_mapping_status",
    "gdp_share_conversion_status",
    "uncertainty_interval_status",
    "replication_status",
    "robustness_transport_status",
    "provenance_status",
    "promotion_status",
    "research_parameterization_admission_status",
    "candidate_gdp_share_drag_per_100bp_year",
    "candidate_ci_lower",
    "candidate_ci_upper",
    "bps_year_exposure_output",
    "exact_blocker",
    "next_backend_action",
    *FORBIDDEN_SWITCHES,
    "claim_boundary",
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _download(url: str, path: Path) -> tuple[bool, str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            data = resp.read()
    except (TimeoutError, urllib.error.URLError, urllib.error.HTTPError) as exc:
        browser_ok, browser_message = _download_with_playwright_request(url, path)
        if browser_ok:
            return True, f"playwright_request_after_{type(exc).__name__}"
        return False, f"{type(exc).__name__}:{exc};{browser_message}"
    path.write_bytes(data)
    return True, "downloaded"


def _download_with_playwright_request(url: str, path: Path) -> tuple[bool, str]:
    """Fallback for public sources that block simple urllib clients."""
    script = """
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright

url = sys.argv[1]
out_path = Path(sys.argv[2])
with sync_playwright() as p:
    request = p.request.new_context(extra_http_headers={
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ),
        "Accept": (
            "application/pdf,text/html,application/xhtml+xml,application/xml;"
            "q=0.9,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.cmegroup.com/",
    })
    response = request.get(url, timeout=45000)
    if response.status >= 400:
        raise RuntimeError(f"HTTP {response.status}")
    out_path.write_bytes(response.body())
"""
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", suffix=".py", delete=False
    ) as handle:
        handle.write(script)
        script_path = Path(handle.name)
    try:
        result = subprocess.run(
            ["python3", str(script_path), url, str(path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"playwright_request_unavailable:{type(exc).__name__}:{exc}"
    finally:
        try:
            script_path.unlink()
        except OSError:
            pass
    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip().replace("\n", " ")
        return False, f"playwright_request_failed:{message}"
    if not path.exists() or path.stat().st_size == 0:
        return False, "playwright_request_empty_response"
    return True, "playwright_request_downloaded"


def _acquire_target(target: ArtifactTarget, directory: Path) -> dict[str, str]:
    directory.mkdir(parents=True, exist_ok=True)
    local_path = directory / target.local_name
    attempts: list[str] = []
    if local_path.exists() and local_path.stat().st_size > 0:
        status = "present_existing"
        used_url = ""
    else:
        status = "blocked_source_artifact_not_acquired"
        used_url = ""
        for url in target.urls:
            ok, message = _download(url, local_path)
            attempts.append(f"{url}::{message}")
            if ok:
                status = "downloaded"
                used_url = url
                break
        if status != "downloaded" and local_path.exists():
            local_path.unlink()
    if local_path.exists() and local_path.stat().st_size > 0:
        artifact_path = local_path.relative_to(ROOT).as_posix()
        artifact_sha256 = _sha256(local_path)
        artifact_size = str(local_path.stat().st_size)
        parser_status = _parser_status(local_path, target.parser_hint)
    else:
        artifact_path = ""
        artifact_sha256 = ""
        artifact_size = "0"
        parser_status = "blocked_source_artifact_not_acquired"
    return {
        "source_candidate_handle": target.source_candidate_handle,
        "source_family": target.source_family,
        "artifact_handle": target.artifact_handle,
        "artifact_path": artifact_path,
        "artifact_sha256": artifact_sha256,
        "artifact_size_bytes": artifact_size,
        "source_url_or_citation_handle": target.source_url_or_citation_handle,
        "source_type": target.source_type,
        "replication_package_available": target.replication_package_available,
        "parser_status": parser_status,
        "parsed_variable_or_file": _parsed_file_summary(local_path)
        if artifact_path
        else "",
        "shock_definition_text": target.shock_definition_text,
        "acquisition_status": status,
        "used_url": used_url,
        "attempts": attempts,
    }


def _parser_status(path: Path, parser_hint: str) -> str:
    suffix = path.suffix.lower()
    if suffix in {".html", ".htm"}:
        return f"pass_metadata_text_parsed_review_only:{parser_hint}"
    if suffix in {".pdf", ".zip", ".xlsx", ".xls", ".m", ".csv"}:
        return f"pass_source_file_hashed_not_economic_output_parsed:{parser_hint}"
    return f"pass_artifact_hashed_review_only:{parser_hint}"


def _parsed_file_summary(path: Path) -> str:
    if not path.exists():
        return ""
    suffix = path.suffix.lower()
    if suffix not in {".html", ".htm", ".txt", ".csv", ".m"}:
        return path.name
    text = path.read_text(encoding="utf-8", errors="ignore")
    links = re.findall(r"href=[\"']([^\"']+)[\"']", text, flags=re.IGNORECASE)
    zip_links = [link for link in links if ".zip" in link.lower()]
    data_links = [
        link for link in links if any(ext in link.lower() for ext in [".xlsx", ".csv", ".m"])
    ]
    snippets = []
    if zip_links:
        snippets.append(f"zip_links={len(zip_links)}")
    if data_links:
        snippets.append(f"data_or_code_links={len(data_links)}")
    return ";".join(snippets) or path.name


def _acquire_openicpsr_target(target: OpenICPSRTarget) -> dict[str, str]:
    RESEARCH_RAW_DIR.mkdir(parents=True, exist_ok=True)
    local_path = RESEARCH_RAW_DIR / target.local_name
    attempts: list[str] = []
    if local_path.exists() and local_path.stat().st_size > 0:
        status = "present_existing"
    else:
        status = "blocked_metadata_artifact_not_acquired"
        for url in target.urls:
            ok, message = _download(url, local_path)
            attempts.append(f"{url}::{message}")
            if ok:
                status = "downloaded"
                break
        if status != "downloaded" and local_path.exists():
            local_path.unlink()
    if local_path.exists() and local_path.stat().st_size > 0:
        artifact_path = local_path.relative_to(ROOT).as_posix()
        artifact_sha256 = _sha256(local_path)
        artifact_size = str(local_path.stat().st_size)
        parser_status = "pass_openicpsr_metadata_artifact_hashed_review_only"
        parsed = _parse_openicpsr_metadata(local_path)
    else:
        artifact_path = ""
        artifact_sha256 = ""
        artifact_size = "0"
        parser_status = "blocked_openicpsr_metadata_artifact_not_acquired"
        parsed = {}
    payload = _attempt_openicpsr_payload(target, local_path if local_path.exists() else None)
    return {
        "source_candidate_handle": target.source_candidate_handle,
        "project_id": target.project_id,
        "version_id": target.version_id,
        "package_object_handle": target.package_object_handle,
        "package_object_path": target.package_object_path,
        "object_kind": target.object_kind,
        "expected_file_type": target.expected_file_type,
        "expected_size_label": target.expected_size_label,
        "candidate_review_role": target.candidate_review_role,
        "source_url_or_citation_handle": target.source_url_or_citation_handle,
        "metadata_artifact_path": artifact_path,
        "metadata_artifact_sha256": artifact_sha256,
        "metadata_artifact_size_bytes": artifact_size,
        "metadata_acquisition_status": status,
        "download_attempt_status": (
            "blocked_direct_package_download_not_acquired_terms_or_cloudflare"
        ),
        "download_attempts": "|".join(attempts),
        "parser_status": parser_status,
        **parsed,
        **payload,
    }


def _attempt_openicpsr_payload(
    target: OpenICPSRTarget, metadata_path: Path | None
) -> dict[str, str]:
    if target.object_kind not in {"file_page_html", "folder_page_html"}:
        return _openicpsr_payload_block(
            "not_applicable_metadata_only_object",
            "",
            "",
            "",
            "",
            "",
        )
    download_url = _openicpsr_download_terms_url(target, metadata_path)
    if not download_url:
        return _openicpsr_payload_block(
            "blocked_no_download_terms_link_discovered",
            "",
            "",
            "",
            "",
            "",
        )
    payload_dir = RESEARCH_RAW_DIR / "openicpsr_payloads"
    payload_dir.mkdir(parents=True, exist_ok=True)
    payload_path = payload_dir / _openicpsr_payload_local_name(target)
    request = urllib.request.Request(download_url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            data = resp.read()
            content_type = resp.headers.get("content-type", "")
            final_url = resp.geturl()
            status = str(resp.status)
    except urllib.error.HTTPError as exc:
        return _openicpsr_payload_block(
            "blocked_http_error_from_download_terms_route",
            download_url,
            getattr(exc, "url", "") or "",
            str(exc.code),
            f"HTTPError:{exc}",
            "",
        )
    except (TimeoutError, urllib.error.URLError) as exc:
        return _openicpsr_payload_block(
            "blocked_network_error_from_download_terms_route",
            download_url,
            "",
            "",
            f"{type(exc).__name__}:{exc}",
            "",
        )
    text_head = data[:20000].decode("utf-8", errors="ignore")
    if _openicpsr_response_is_login(final_url, text_head):
        return _openicpsr_payload_block(
            "blocked_login_required_from_download_terms_route",
            download_url,
            final_url,
            status,
            f"content_type={content_type};bytes={len(data)}",
            "",
        )
    if _openicpsr_response_is_terms_or_html(content_type, text_head):
        return _openicpsr_payload_block(
            "blocked_terms_or_html_interstitial_from_download_terms_route",
            download_url,
            final_url,
            status,
            f"content_type={content_type};bytes={len(data)}",
            "",
        )
    payload_path.write_bytes(data)
    return {
        "source_file_payload_path": payload_path.relative_to(ROOT).as_posix(),
        "source_file_payload_sha256": _sha256(payload_path),
        "source_file_payload_size_bytes": str(payload_path.stat().st_size),
        "source_file_payload_status": "pass_openicpsr_payload_downloaded_review_only",
        "source_file_payload_download_url": download_url,
        "source_file_payload_final_url": final_url,
        "source_file_payload_http_status": status,
        "source_file_payload_blocker_class": "",
        "source_file_payload_attempts": f"content_type={content_type};bytes={len(data)}",
    }


def _openicpsr_payload_block(
    blocker_class: str,
    download_url: str,
    final_url: str,
    http_status: str,
    attempts: str,
    payload_path: str,
) -> dict[str, str]:
    return {
        "source_file_payload_path": payload_path,
        "source_file_payload_sha256": "",
        "source_file_payload_size_bytes": "",
        "source_file_payload_status": (
            "blocked_openicpsr_payload_not_downloaded_terms_or_cloudflare"
        ),
        "source_file_payload_download_url": download_url,
        "source_file_payload_final_url": final_url,
        "source_file_payload_http_status": http_status,
        "source_file_payload_blocker_class": blocker_class,
        "source_file_payload_attempts": attempts,
    }


def _openicpsr_download_terms_url(
    target: OpenICPSRTarget, metadata_path: Path | None
) -> str:
    if metadata_path and metadata_path.exists():
        text = metadata_path.read_text(encoding="utf-8", errors="ignore")
        links = re.findall(r"href=[\"']([^\"']+download/terms[^\"']+)", text)
        if links:
            return urllib.parse.urljoin(
                "https://www.openicpsr.org/openicpsr/",
                _html_unescape(links[0]),
            )
    object_type = "folder" if target.object_kind == "folder_page_html" else "file"
    return (
        "https://www.openicpsr.org/openicpsr/project/"
        f"{target.project_id}/version/{target.version_id}/download/terms?"
        f"path={urllib.parse.quote(target.package_object_path, safe='/:')}"
        f"&type={object_type}"
    )


def _openicpsr_payload_local_name(target: OpenICPSRTarget) -> str:
    suffix = ".zip" if target.object_kind == "folder_page_html" else Path(
        target.package_object_path
    ).suffix
    if not suffix:
        suffix = ".bin"
    return f"{target.project_id}_{target.package_object_handle}{suffix}"


def _openicpsr_response_is_login(final_url: str, text: str) -> bool:
    return (
        "login.icpsr.umich.edu" in final_url
        or "Sign in to icpsr" in text
        or "kc-form-login" in text
    )


def _openicpsr_response_is_terms_or_html(content_type: str, text: str) -> bool:
    lowered_type = content_type.lower()
    lowered_text = text.lower()
    return (
        "text/html" in lowered_type
        or "<html" in lowered_text
        or "download terms" in lowered_text
        or "terms of use" in lowered_text
    )


def _parse_openicpsr_metadata(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    clean = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()
    title = _first_match(text, r"<title>(.*?)</title>") or _first_match(
        text, r"<dc:title>(.*?)</dc:title>"
    )
    rows = _parse_openicpsr_table_rows(text)
    child_objects = ";".join(
        f"{row.get('name', '')}|{row.get('file_type', '')}|{row.get('size', '')}"
        for row in rows[:40]
        if row.get("name")
    )
    first_file = rows[0] if len(rows) == 1 else {}
    candidate_names = [
        row.get("name", "")
        for row in rows
        if row.get("name")
        and any(
            token in row.get("name", "").lower()
            for token in [
                ".m",
                ".mat",
                ".xlsx",
                ".xls",
                ".csv",
                ".pdf",
                "readme",
                "data",
                "figure",
                "table",
                "var",
                "svar",
                "proxy",
            ]
        )
    ]
    code_count = sum(
        1
        for row in rows
        if any(
            token in row.get("name", "").lower()
            for token in [".m", ".do", ".r", ".py", ".sas", ".asv", "code"]
        )
    )
    data_count = sum(
        1
        for row in rows
        if any(
            token in row.get("name", "").lower()
            for token in [".xlsx", ".xls", ".csv", ".mat", ".dta", "data"]
        )
    )
    readme_count = sum(1 for row in rows if "readme" in row.get("name", "").lower())
    inventory_tokens = sorted(
        {
            token
            for token in [
                "README" if re.search(r"readme", clean, re.IGNORECASE) else "",
                "VAR_main_RunMe.m"
                if re.search(r"VAR_main_RunMe\.m", clean, re.IGNORECASE)
                else "",
                "BUILD_data.m"
                if re.search(r"BUILD_data\.m", clean, re.IGNORECASE)
                else "",
                "ALLDATA.xlsx"
                if re.search(r"ALLDATA\.xlsx", clean, re.IGNORECASE)
                else "",
                "Replicate_Figure*.m"
                if re.search(r"Replicate_Figure", clean, re.IGNORECASE)
                else "",
                "MATfiles" if re.search(r"MATfiles|\.mat", clean, re.IGNORECASE) else "",
                "ProxySVAR"
                if re.search(r"ProxySVAR|external instrument", clean, re.IGNORECASE)
                else "",
            ]
            if token
        }
    )
    return {
        "parsed_title_or_name": _html_unescape(title or "")[:240],
        "parsed_file_type": first_file.get("file_type", ""),
        "parsed_size_label": first_file.get("size", ""),
        "parsed_last_modified": first_file.get("last_modified", ""),
        "parsed_child_objects": child_objects,
        "parsed_file_manifest_entry_count": str(len(rows)),
        "parsed_code_entry_count": str(code_count),
        "parsed_data_entry_count": str(data_count),
        "parsed_readme_entry_count": str(readme_count),
        "parsed_candidate_file_names": ";".join(candidate_names[:80]),
        "candidate_variable_or_irf_names": ";".join(
            name
            for name in candidate_names[:80]
            if any(
                token in name.lower()
                for token in [
                    "figure",
                    "irf",
                    "var",
                    "svar",
                    "proxy",
                    "weight",
                    "replicate",
                    ".mat",
                ]
            )
        ),
        "candidate_variable_or_file_inventory": ";".join(inventory_tokens),
    }


def _first_match(text: str, pattern: str) -> str:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else ""


def _html_unescape(value: str) -> str:
    return (
        value.replace("&amp;", "&")
        .replace("&nbsp;", " ")
        .replace("&#39;", "'")
        .replace("&quot;", '"')
    )


def _parse_openicpsr_table_rows(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for match in re.finditer(r"<tr>(.*?)</tr>", text, flags=re.IGNORECASE | re.DOTALL):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", match.group(1), flags=re.IGNORECASE | re.DOTALL)
        if len(cells) < 4:
            continue
        name_cell = cells[0]
        name = _html_unescape(re.sub(r"<[^>]+>", " ", name_cell))
        name = re.sub(r"\s+", " ", name).strip()
        file_type = _html_unescape(re.sub(r"<[^>]+>", " ", cells[1]))
        file_type = re.sub(r"\s+", " ", file_type).strip()
        size = _html_unescape(re.sub(r"<[^>]+>", " ", cells[2]))
        size = re.sub(r"\s+", " ", size).strip()
        last_modified = _html_unescape(re.sub(r"<[^>]+>", " ", cells[3]))
        last_modified = re.sub(r"\s+", " ", last_modified).strip()
        if name:
            rows.append(
                {
                    "name": name,
                    "file_type": file_type,
                    "size": size,
                    "last_modified": last_modified,
                }
            )
    return rows


def _openicpsr_review_statuses(item: dict[str, str]) -> dict[str, str]:
    role = item["candidate_review_role"]
    inventory = item.get("candidate_variable_or_file_inventory", "")
    candidate_names = item.get("parsed_candidate_file_names", "")
    irf_names = item.get("candidate_variable_or_irf_names", "")
    has_artifact = bool(item.get("metadata_artifact_sha256"))
    has_readme = (
        "README" in inventory
        or role == "readme"
        or int(item.get("parsed_readme_entry_count") or "0") > 0
    )
    has_code = role.endswith("code_inventory") or role in {
        "irf_figure_code_inventory",
        "proxy_svar_code_inventory",
    } or any(
        token in inventory
        for token in ["VAR_main_RunMe.m", "BUILD_data.m", "Replicate_Figure*.m"]
    ) or int(item.get("parsed_code_entry_count") or "0") > 0
    has_data = (
        role == "data_workbook_inventory"
        or "ALLDATA.xlsx" in inventory
        or int(item.get("parsed_data_entry_count") or "0") > 0
    )
    has_irf = role in {
        "irf_figure_code_inventory",
        "proxy_svar_code_inventory",
        "code_inventory",
    } or any(
        token in inventory
        for token in ["Replicate_Figure*.m", "VAR_main_RunMe.m", "ProxySVAR"]
    ) or bool(irf_names)
    return {
        "candidate_variable_inventory_status": (
            "pass_metadata_inventory_signals_present_review_only"
            if inventory or candidate_names
            else "blocked_no_parsed_variable_inventory"
        ),
        "candidate_irf_availability_status": (
            "pass_irf_or_svar_code_metadata_present_review_only"
            if has_irf
            else "blocked_no_parsed_irf_array_or_svar_output"
        ),
        "candidate_uncertainty_availability_status": (
            "blocked_no_parsed_uncertainty_array_or_confidence_interval"
        ),
        "candidate_readme_status": (
            "pass_readme_metadata_present_review_only"
            if has_readme and has_artifact
            else "blocked_readme_not_reproducibly_downloaded_or_parsed"
        ),
        "candidate_code_status": (
            "pass_code_metadata_present_review_only"
            if has_code and has_artifact
            else "blocked_code_file_not_reproducibly_downloaded_or_parsed"
        ),
        "candidate_data_status": (
            "pass_data_metadata_present_review_only"
            if has_data and has_artifact
            else "blocked_data_file_not_reproducibly_downloaded_or_parsed"
        ),
    }


def _openicpsr_manifest_rows(
    acquired_items: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in acquired_items:
        statuses = _openicpsr_review_statuses(item)
        row = {
            "manifest_row_id": (
                "openicpsr_replication_package_manifest::"
                f"{item['source_candidate_handle']}::"
                f"{item['package_object_handle']}"
            ),
            **item,
            **statuses,
            "shock_definition_status": (
                "candidate_monetary_policy_shock_family_metadata_present_review_only"
            ),
            "shock_normalization_status": (
                "blocked_no_100bp_year_compatible_shock_normalization_review"
            ),
            "policy_path_exposure_definition_status": (
                "blocked_no_admitted_bps_year_policy_path"
            ),
            "current_demand_mapping_status": (
                "blocked_no_current_demand_component_mapping_from_package"
            ),
            "gdp_share_conversion_status": "blocked_no_gdp_share_conversion",
            "uncertainty_interval_status": (
                "blocked_no_extracted_parameter_uncertainty_interval"
            ),
            "replication_status": "blocked_no_local_replication_run_or_tolerance",
            "robustness_transport_status": (
                "blocked_no_ratewall_transport_or_robustness_review"
            ),
            "provenance_status": (
                "pass_metadata_artifact_hashed_review_only"
                if item.get("metadata_artifact_sha256")
                else "blocked_no_local_metadata_hash"
            ),
            "promotion_status": "blocked_no_promotion_rule",
            "research_parameterization_admission_status": (
                "blocked_openicpsr_manifest_not_denominator_calibration"
            ),
            "candidate_gdp_share_drag_per_100bp_year": "",
            "candidate_ci_lower": "",
            "candidate_ci_upper": "",
            "bps_year_exposure_output": "",
            "exact_blocker": (
                "openICPSR metadata or file-page inventory does not provide an "
                "admitted GDP-share current-demand drag per 100bp-year estimate "
                "with compatible shock normalization, uncertainty, replication, "
                "robustness, provenance, and promotion."
            ),
            "next_backend_action": (
                "acquire_reproducible_package_files_and_parse_readme_code_data_"
                "before_any_research_parameterization"
            ),
            "claim_boundary": (
                "openicpsr_replication_package_manifest_not_denominator_or_runtime_input"
            ),
        }
        for switch in FORBIDDEN_SWITCHES:
            row[switch] = "false"
        rows.append(row)
    return rows


def _research_frontier_rows(artifacts: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for artifact in artifacts:
        for field_name, blocker, next_action in REQUIRED_CONTRACT_FIELDS:
            row = {
                "frontier_row_id": (
                    "conventional_drag_source_frontier::"
                    f"{artifact['source_candidate_handle']}::"
                    f"{artifact['artifact_handle']}::{field_name}"
                ),
                "source_candidate_handle": artifact["source_candidate_handle"],
                "source_family": artifact["source_family"],
                "artifact_handle": artifact["artifact_handle"],
                "artifact_path": artifact["artifact_path"],
                "artifact_sha256": artifact["artifact_sha256"],
                "artifact_size_bytes": artifact["artifact_size_bytes"],
                "source_url_or_citation_handle": artifact[
                    "source_url_or_citation_handle"
                ],
                "source_type": artifact["source_type"],
                "replication_package_available": artifact[
                    "replication_package_available"
                ],
                "parser_status": artifact["parser_status"],
                "parsed_variable_or_file": artifact["parsed_variable_or_file"],
                "required_contract_field": field_name,
                "shock_definition_text": artifact["shock_definition_text"],
                "shock_unit_status": (
                    "blocked_no_100bp_year_compatible_unit_review"
                ),
                "policy_path_exposure_definition_status": (
                    "blocked_no_admitted_bps_year_policy_path"
                ),
                "current_demand_mapping_status": (
                    "blocked_no_current_demand_gdp_share_mapping"
                ),
                "gdp_share_conversion_status": "blocked_no_gdp_share_conversion",
                "uncertainty_interval_status": (
                    "blocked_no_parameter_uncertainty_interval"
                ),
                "replication_status": (
                    "blocked_no_ratewall_parameter_replication"
                ),
                "robustness_transport_status": (
                    "blocked_no_transport_robustness_review"
                ),
                "provenance_status": "pass_artifact_hashed_review_only"
                if artifact["artifact_sha256"]
                else "blocked_no_local_artifact_hash",
                "research_parameterization_admission_status": (
                    "blocked_missing_full_research_parameterization_contract"
                ),
                "candidate_gdp_share_drag_per_100bp_year": "",
                "candidate_ci_lower": "",
                "candidate_ci_upper": "",
                "exact_blocker": blocker,
                "next_backend_action": next_action,
                "claim_boundary": (
                    "research_parameterization_source_frontier_not_denominator_"
                    "calibration"
                ),
            }
            for switch in FORBIDDEN_SWITCHES:
                row[switch] = "false"
            rows.append(row)
    return rows


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_csv(path: Path, fields: list[str], rows: Iterable[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def _quarter_start(d: date, offset: int) -> date:
    quarter = (d.month - 1) // 3 + offset
    year = d.year + quarter // 4
    q_index = quarter % 4
    return date(year, q_index * 3 + 1, 1)


def _month_start(d: date, offset: int) -> date:
    month_index = d.month - 1 + offset
    return date(d.year + month_index // 12, month_index % 12 + 1, 1)


def _month_end(d: date) -> date:
    return date(d.year, d.month, monthrange(d.year, d.month)[1])


def _third_wednesday(year: int, month: int) -> date:
    first_day = date(year, month, 1)
    days_until_wednesday = (2 - first_day.weekday()) % 7
    first_wednesday = date.fromordinal(first_day.toordinal() + days_until_wednesday)
    return date.fromordinal(first_wednesday.toordinal() + 14)


def _quarterly_delivery_month(d: date, offset: int) -> date:
    quarter_start = _quarter_start(d, offset)
    return _month_start(quarter_start, 2)


def _reference_interval(
    event_date: str, instrument: str
) -> tuple[str, str, str, str, str]:
    d = date.fromisoformat(event_date)
    if instrument == "FF1":
        start = _month_start(d, 0)
        end = _month_end(start)
        delivery = start.strftime("%Y-%m")
        rule_status = (
            "source_label_current_month_delivery_month_rule_reviewed_not_"
            "admitted_mapping"
        )
        interval_status = "fed_funds_delivery_month_metadata_only_not_bps_year_weight"
    elif instrument == "FF2":
        start = _month_start(d, 1)
        end = _month_end(start)
        delivery = start.strftime("%Y-%m")
        rule_status = (
            "source_label_next_month_delivery_month_rule_reviewed_not_"
            "admitted_mapping"
        )
        interval_status = "fed_funds_delivery_month_metadata_only_not_bps_year_weight"
    else:
        slot = int(instrument[-1]) - 1
        delivery_month = _quarterly_delivery_month(d, slot)
        delivery = delivery_month.strftime("%Y-%m")
        third_wednesday = _third_wednesday(delivery_month.year, delivery_month.month)
        if d >= date(2023, 1, 1):
            start_month = _month_start(delivery_month, -3)
            start = _third_wednesday(start_month.year, start_month.month)
            end = date.fromordinal(third_wednesday.toordinal() - 1)
            rule_status = (
                "sofr_chapter_460_reference_quarter_third_wednesday_rule_"
                "reviewed_not_admitted_mapping"
            )
            interval_status = (
                "sofr_reference_quarter_metadata_only_not_bps_year_weight"
            )
        else:
            start = third_wednesday
            next_delivery_month = _month_start(delivery_month, 3)
            next_third_wednesday = _third_wednesday(
                next_delivery_month.year, next_delivery_month.month
            )
            end = date.fromordinal(next_third_wednesday.toordinal() - 1)
            rule_status = (
                "eurodollar_imm_third_wednesday_delivery_context_reviewed_"
                "not_admitted_mapping"
            )
            interval_status = (
                "eurodollar_imm_term_context_metadata_only_not_bps_year_weight"
            )
    return (
        delivery,
        start.isoformat(),
        end.isoformat(),
        rule_status,
        interval_status,
    )


def _year_fraction(start: str, end: str) -> str:
    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)
    days = (end_date - start_date).days + 1
    return f"{days / 365.25:.6f}"


def _overlap_after_event(event_date: str, start: str, end: str) -> tuple[str, str]:
    event = date.fromisoformat(event_date)
    start_date = max(date.fromisoformat(start), event)
    end_date = date.fromisoformat(end)
    days = max(0, (end_date - start_date).days + 1)
    return str(days), f"{days / 365.25:.6f}"


def _literal_na_status(row: dict[str, str]) -> str:
    value = row.get("source_reported_value_raw") or row.get("raw_workbook_value", "")
    numeric = row.get("source_reported_value_numeric", "")
    if value.strip().upper() == "NA":
        return "source_literal_na"
    if value.strip() == "":
        return "source_blank"
    if numeric:
        return "source_numeric"
    return "source_non_numeric"


def _contract_source_for_row(
    row: dict[str, str], artifacts_by_handle: dict[str, dict[str, str]]
) -> tuple[str, str, str, str]:
    instrument = row.get("instrument_code", "")
    event = row.get("event_date", "")
    if instrument in {"FF1", "FF2"}:
        handle = "cme_cbot_chapter_22_fed_funds_pdf"
        source_handle = "cme_cbot_chapter_22_fed_funds"
    elif event >= "2023-01-01":
        handle = "cme_chapter_460_sofr_pdf"
        source_handle = "cme_chapter_460_sofr"
    else:
        handle = "cme_eurodollar_futures_foundational_concepts_pdf"
        source_handle = "cme_eurodollar_futures_foundational_concepts"
    artifact = artifacts_by_handle.get(handle, {})
    status = (
        "pass_official_spec_artifact_hashed"
        if artifact.get("artifact_sha256")
        else "blocked_official_spec_artifact_not_acquired"
    )
    return (
        source_handle,
        artifact.get("artifact_path", ""),
        artifact.get("artifact_sha256", ""),
        status,
    )


def _quote_rule(instrument: str, event_date: str) -> str:
    if instrument in {"FF1", "FF2"}:
        return (
            "official_spec_review_metadata: 30-day fed funds futures quoted as "
            "100 minus average effective federal funds rate for delivery month"
        )
    if event_date >= "2023-01-01":
        return (
            "official_spec_review_metadata: three-month SOFR futures quoted as "
            "100 minus compounded SOFR during the Chapter 460 third-Wednesday "
            "reference quarter"
        )
    return (
        "official_spec_review_metadata: Eurodollar futures quoted as 100 minus "
        "three-month LIBOR for IMM third-Wednesday delivery-month settlement "
        "context"
    )


def _contract_review_rows(artifacts: list[dict[str, str]]) -> list[dict[str, str]]:
    candidate_rows = _read_csv(CANDIDATE_VECTOR_CSV)
    artifacts_by_handle = {item["artifact_handle"]: item for item in artifacts}
    rows: list[dict[str, str]] = []
    for item in candidate_rows:
        instrument = item.get("instrument_code", "")
        event_date = item.get("event_date", "")
        (
            delivery,
            ref_start,
            ref_end,
            delivery_rule_status,
            interval_weight_status,
        ) = _reference_interval(event_date, instrument)
        overlap_days, overlap_years = _overlap_after_event(
            event_date, ref_start, ref_end
        )
        spec_handle, spec_path, spec_hash, spec_status = _contract_source_for_row(
            item, artifacts_by_handle
        )
        literal_status = _literal_na_status(item)
        row = {
            "contract_review_row_id": (
                "policy_path_contract_interval_review::"
                f"{item.get('source_sheet_vintage', '')}::"
                f"{item.get('event_sequence', '')}::{instrument}"
            ),
            "candidate_vector_row_id": item.get("candidate_vector_row_id", ""),
            "source_sheet_vintage": item.get("source_sheet_vintage", ""),
            "source_sheet_name": item.get("source_sheet_name", ""),
            "event_id": item.get("event_id", ""),
            "event_date": event_date,
            "event_time": item.get("event_time", ""),
            "candidate_instrument_code": instrument,
            "source_cell_value_text": item.get("source_reported_value_raw", ""),
            "source_cell_value_numeric": item.get(
                "source_reported_value_numeric", ""
            ),
            "literal_na_status": literal_status,
            "instrument_family": item.get("instrument_family", ""),
            "official_spec_source_handle": spec_handle,
            "official_spec_artifact_path": spec_path,
            "official_spec_artifact_sha256": spec_hash,
            "official_spec_acquisition_status": spec_status,
            "price_quote_rule": _quote_rule(instrument, event_date),
            "rate_to_price_sign_status": (
                "review_metadata_quote_is_100_minus_rate_not_runtime_sign_rule"
            ),
            "source_unit_status": (
                "contract_spec_unit_context_reviewed_but_source_cell_unit_"
                "conversion_still_blocked"
            ),
            "candidate_delivery_month": delivery,
            "delivery_month_selection_rule_status": delivery_rule_status,
            "reference_period_start": ref_start,
            "reference_period_end": ref_end,
            "reference_period_year_fraction": _year_fraction(ref_start, ref_end),
            "event_overlap_days": overlap_days,
            "event_overlap_year_fraction": overlap_years,
            "candidate_interval_weight_status": interval_weight_status,
            "policy_rate_bps_exposure": "",
            "bps_year_component": "",
            "bps_year_exposure_output": "",
            "candidate_gdp_share_drag_per_100bp_year": "",
            "bps_year_integration_status": (
                "blocked_no_reviewed_bps_year_integration_formula"
            ),
            "independent_replication_status": (
                "blocked_no_bps_year_replication_target"
            ),
            "protocol_admission_status": (
                "blocked_contract_interval_review_not_bps_year_protocol"
            ),
            "source_admission_status": (
                "blocked_contract_interval_candidate_review_only"
            ),
            "exact_blocker": (
                "Official contract-spec interval metadata can support source "
                "review, but RateWall still lacks a reviewed source-cell unit "
                "conversion, bps-year integration formula, independent "
                "replication target, and promotion rule."
            ),
            "next_backend_action": (
                "review_unit_conversion_and_bps_year_integration_formula_before_"
                "any_policy_path_promotion"
            ),
            "claim_boundary": (
                "contract_interval_review_not_bps_year_or_runtime_input"
            ),
        }
        if literal_status == "source_literal_na":
            row["candidate_interval_weight_status"] = (
                "source_literal_na_preserved_no_interval_weight"
            )
        for switch in FORBIDDEN_SWITCHES:
            row[switch] = "false"
        rows.append(row)
    return rows


def _write_manifest(
    path: Path,
    artifacts: list[dict[str, str]],
    output_path: Path,
    rows: list[dict[str, str]],
) -> None:
    payload = {
        "parser_name": Path(__file__).name,
        "parser_version": "2026-05-22.1",
        "output_path": output_path.relative_to(ROOT).as_posix(),
        "output_sha256": _sha256(output_path) if output_path.exists() else "",
        "output_row_count": len(rows),
        "source_artifacts": artifacts,
        "admission_status": "blocked_review_only_not_runtime_input",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _zip_manifest(path: Path) -> tuple[list[dict[str, str]], int]:
    if not path.exists() or path.suffix.lower() != ".zip":
        return [], 0
    rows: list[dict[str, str]] = []
    with zipfile.ZipFile(path) as archive:
        infos = [info for info in archive.infolist() if not info.is_dir()]
        for info in infos:
            payload = archive.read(info.filename)
            rows.append(
                {
                    "name": info.filename,
                    "size": str(info.file_size),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }
            )
    return rows, len(rows)


def _zip_text(path: Path, entry_name: str) -> str:
    try:
        with zipfile.ZipFile(path) as archive:
            return archive.read(entry_name).decode("utf-8", errors="ignore")
    except (KeyError, zipfile.BadZipFile, FileNotFoundError):
        return ""


def _csv_header_from_zip(path: Path, entry_name: str) -> list[str]:
    text = _zip_text(path, entry_name)
    if not text:
        return []
    try:
        return next(csv.reader([text.splitlines()[0]]))
    except (StopIteration, csv.Error):
        return []


def _frbus_candidate_summary(path: Path, artifact_handle: str) -> dict[str, str]:
    if artifact_handle == "frbus_python_package_zip":
        example_hits: list[str] = []
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if not name.startswith("pyfrbus/demos/") or not name.endswith(".py"):
                    continue
                text = archive.read(name).decode("utf-8", errors="ignore")
                if "rffintay_aerr" in text or "rff_t" in text:
                    example_hits.append(name)
        model_text = _zip_text(path, "pyfrbus/models/model.xml").lower()
        variables = [
            variable
            for variable in ["rff", "rffintay", "rffrule", "xgdp", "ec", "ebfi", "ei"]
            if f"<name>{variable}</name>" in model_text
        ]
        return {
            "candidate_file_or_variable": ";".join(sorted(example_hits + variables)),
            "policy_hook": "pass_candidate_policy_rate_hook_present"
            if example_hits
            else "blocked_no_policy_hook_candidate_found",
            "gdp": "pass_candidate_gdp_variable_present"
            if "xgdp" in variables
            else "blocked_no_gdp_variable_candidate_found",
            "pce": "pass_candidate_pce_variable_present"
            if "ec" in variables
            else "blocked_no_pce_variable_candidate_found",
            "investment": "pass_candidate_investment_variable_present"
            if "ebfi" in variables or "ei" in variables
            else "blocked_no_investment_variable_candidate_found",
        }
    headers: set[str] = set()
    for entry in ("data_only_package/LONGBASE.TXT", "data_only_package/HISTDATA.TXT"):
        headers.update(_csv_header_from_zip(path, entry))
    return {
        "candidate_file_or_variable": ";".join(
            token
            for token in [
                "RFF",
                "RFFINTAY",
                "RFFRULE",
                "RFFTAY",
                "XGDP",
                "FGDP",
                "HGGDP",
                "EC",
                "ECD",
                "EBFI",
                "EI",
                "EX",
            ]
            if token in headers
        ),
        "policy_hook": "pass_candidate_policy_rate_series_present"
        if {"RFF", "RFFINTAY"} & headers
        else "blocked_no_policy_rate_series_candidate_found",
        "gdp": "pass_candidate_gdp_series_present"
        if {"XGDP", "FGDP", "HGGDP"} & headers
        else "blocked_no_gdp_series_candidate_found",
        "pce": "pass_candidate_pce_series_present"
        if {"EC", "ECD"} & headers
        else "blocked_no_pce_series_candidate_found",
        "investment": "pass_candidate_investment_series_present"
        if {"EBFI", "EI"} & headers
        else "blocked_no_investment_series_candidate_found",
    }


def _frbus_readiness_rows(artifacts: list[dict[str, str]]) -> list[dict[str, str]]:
    required_fields = [
        (
            "file_manifest",
            "pass_file_manifest_hashed",
            "FRB/US package file manifest is present, but this does not admit a denominator value.",
        ),
        (
            "policy_shock_hook",
            "blocked_no_admitted_policy_shock_simulation_protocol",
            "Review and implement a source-backed FRB/US shock protocol before simulation use.",
        ),
        (
            "gdp_outcome_availability",
            "blocked_no_gdp_share_response_extraction",
            "Map FRB/US GDP variables to a GDP-share current-demand response before any parameterization.",
        ),
        (
            "pce_outcome_availability",
            "blocked_no_current_demand_component_mapping",
            "Review whether PCE variables can support current-demand mapping.",
        ),
        (
            "investment_outcome_availability",
            "blocked_no_current_demand_component_mapping",
            "Review whether investment variables can support current-demand mapping.",
        ),
        (
            "uncertainty_interval",
            "blocked_no_empirical_uncertainty_interval",
            "FRB/US package availability does not provide empirical uncertainty for RateWall.",
        ),
        (
            "replication_tolerance",
            "blocked_no_replicated_simulation_output",
            "Run and compare a named FRB/US benchmark simulation before any model-benchmark use.",
        ),
        (
            "promotion_rule",
            "blocked_no_promotion_rule",
            "Define a separate promotion gate; model readiness alone cannot narrow priors.",
        ),
    ]
    rows: list[dict[str, str]] = []
    for artifact in artifacts:
        if artifact["artifact_handle"] not in {
            "frbus_python_package_zip",
            "frbus_data_only_package_zip",
        }:
            continue
        artifact_path = ROOT / artifact["artifact_path"] if artifact["artifact_path"] else Path("")
        manifest_rows, entry_count = _zip_manifest(artifact_path)
        candidate = (
            _frbus_candidate_summary(artifact_path, artifact["artifact_handle"])
            if artifact_path.exists()
            else {}
        )
        file_manifest_hash = hashlib.sha256(
            json.dumps(manifest_rows, sort_keys=True).encode("utf-8")
        ).hexdigest() if manifest_rows else ""
        for readiness_field, blocker, next_action in required_fields:
            row = {
                "readiness_row_id": (
                    "frbus_model_benchmark_simulation_readiness::"
                    f"{artifact['artifact_handle']}::{readiness_field}"
                ),
                "source_candidate_handle": artifact["source_candidate_handle"],
                "artifact_handle": artifact["artifact_handle"],
                "artifact_path": artifact["artifact_path"],
                "artifact_sha256": artifact["artifact_sha256"],
                "artifact_size_bytes": artifact["artifact_size_bytes"],
                "zip_entry_count": str(entry_count),
                "readiness_field": readiness_field,
                "candidate_file_or_variable": candidate.get(
                    "candidate_file_or_variable", ""
                ),
                "candidate_file_sha256": file_manifest_hash,
                "file_manifest_status": "pass_zip_manifest_hashed"
                if manifest_rows
                else "blocked_zip_manifest_not_available",
                "policy_shock_hook_candidate_status": candidate.get(
                    "policy_hook", "blocked_no_policy_hook_candidate_found"
                ),
                "gdp_outcome_candidate_status": candidate.get(
                    "gdp", "blocked_no_gdp_candidate_found"
                ),
                "pce_outcome_candidate_status": candidate.get(
                    "pce", "blocked_no_pce_candidate_found"
                ),
                "investment_outcome_candidate_status": candidate.get(
                    "investment", "blocked_no_investment_candidate_found"
                ),
                "shock_normalization_status": (
                    "blocked_no_ratewall_compatible_frbus_shock_normalization"
                ),
                "gdp_share_conversion_status": (
                    "blocked_no_frbus_response_to_gdp_share_conversion"
                ),
                "uncertainty_interval_status": (
                    "blocked_no_empirical_uncertainty_interval"
                ),
                "replication_status": "blocked_no_replicated_frbus_benchmark_run",
                "promotion_status": "blocked",
                "model_benchmark_admission_status": (
                    "blocked_model_benchmark_readiness_only_not_denominator_value"
                ),
                "candidate_gdp_share_drag_per_100bp_year": "",
                "bps_year_exposure_output": "",
                "exact_blocker": blocker,
                "next_backend_action": next_action,
                "claim_boundary": (
                    "frbus_model_benchmark_readiness_not_empirical_calibration"
                ),
            }
            for switch in FORBIDDEN_SWITCHES:
                row[switch] = "false"
            rows.append(row)
    return rows


def _contract_spec_blocker_rows(
    artifacts: list[dict[str, str]], contract_rows: list[dict[str, str]]
) -> list[dict[str, str]]:
    instrument_by_handle = {
        "cme_cbot_chapter_22_fed_funds_pdf": "FF1;FF2",
        "cme_chapter_460_sofr_pdf": "ED1;ED2;ED3;ED4",
        "cme_eurodollar_futures_foundational_concepts_pdf": "ED1;ED2;ED3;ED4",
    }
    count_by_source: dict[str, int] = {}
    for row in contract_rows:
        count_by_source[row.get("official_spec_source_handle", "")] = (
            count_by_source.get(row.get("official_spec_source_handle", ""), 0) + 1
        )
    rows: list[dict[str, str]] = []
    for artifact in artifacts:
        if artifact["artifact_handle"] not in instrument_by_handle:
            continue
        source_handle = artifact["source_url_or_citation_handle"]
        artifact_hashed = bool(artifact["artifact_sha256"])
        row = {
            "blocker_row_id": (
                "policy_path_contract_spec_acquisition_blocker::"
                f"{artifact['artifact_handle']}"
            ),
            "official_spec_source_handle": source_handle,
            "artifact_handle": artifact["artifact_handle"],
            "requested_urls": ";".join(
                url
                for target in CONTRACT_SPEC_TARGETS
                if target.artifact_handle == artifact["artifact_handle"]
                for url in target.urls
            ),
            "local_artifact_path": artifact["artifact_path"],
            "local_artifact_sha256": artifact["artifact_sha256"],
            "acquisition_status": artifact["acquisition_status"],
            "attempts": ";".join(artifact.get("attempts", [])),
            "affected_candidate_instrument_codes": instrument_by_handle[
                artifact["artifact_handle"]
            ],
            "covered_candidate_row_count": str(count_by_source.get(source_handle, 0)),
            "fallback_path_status": (
                "pass_reproducible_official_spec_artifact_hash_present"
                if artifact_hashed
                else "blocked_no_reproducible_official_spec_artifact_hash"
            ),
            "exact_blocker": (
                "Official contract-spec artifact has been acquired and hashed for "
                "unit/sign/interval review only; RateWall still lacks source-cell "
                "unit conversion, bps-year integration, independent replication, "
                "and a promotion rule."
                if artifact_hashed
                else (
                    "CME official contract-spec URL did not produce a local hashed "
                    "artifact in the automated acquisition path, so RateWall cannot "
                    "mark unit/sign/interval evidence as source-backed."
                )
            ),
            "next_backend_action": (
                "review_hashed_contract_spec_against_source_cell_units_and_bps_"
                "year_integration_formula_before_any_policy_path_promotion"
                if artifact_hashed
                else (
                    "acquire_official_cme_artifact_via_reproducible_source_or_record_"
                    "manual_review_hash_before_bps_year_protocol_use"
                )
            ),
            "claim_boundary": (
                "contract_spec_acquisition_blocker_not_bps_year_or_runtime_input"
            ),
        }
        for switch in FORBIDDEN_SWITCHES:
            row[switch] = "false"
        rows.append(row)
    return rows


def main() -> None:
    research_artifacts = [
        _acquire_target(target, RESEARCH_RAW_DIR)
        for target in RESEARCH_ARTIFACT_TARGETS
    ]
    frontier_rows = _research_frontier_rows(research_artifacts)
    _write_csv(FRONTIER_CSV, FRONTIER_FIELDS, frontier_rows)
    _write_manifest(FRONTIER_MANIFEST, research_artifacts, FRONTIER_CSV, frontier_rows)
    frbus_rows = _frbus_readiness_rows(research_artifacts)
    _write_csv(FRBUS_READINESS_CSV, FRBUS_READINESS_FIELDS, frbus_rows)
    openicpsr_artifacts = [
        _acquire_openicpsr_target(target) for target in OPENICPSR_OBJECT_TARGETS
    ]
    openicpsr_rows = _openicpsr_manifest_rows(openicpsr_artifacts)
    _write_csv(
        OPENICPSR_REPLICATION_PACKAGE_MANIFEST_CSV,
        OPENICPSR_REPLICATION_PACKAGE_MANIFEST_FIELDS,
        openicpsr_rows,
    )
    _write_manifest(
        OPENICPSR_REPLICATION_PACKAGE_ACQUISITION_MANIFEST,
        openicpsr_artifacts,
        OPENICPSR_REPLICATION_PACKAGE_MANIFEST_CSV,
        openicpsr_rows,
    )

    contract_artifacts = [
        _acquire_target(target, CONTRACT_RAW_DIR)
        for target in CONTRACT_SPEC_TARGETS
    ]
    contract_rows = _contract_review_rows(contract_artifacts)
    _write_csv(CONTRACT_REVIEW_CSV, CONTRACT_REVIEW_FIELDS, contract_rows)
    blocker_rows = _contract_spec_blocker_rows(contract_artifacts, contract_rows)
    _write_csv(CONTRACT_BLOCKER_CSV, CONTRACT_BLOCKER_FIELDS, blocker_rows)
    _write_manifest(
        CONTRACT_MANIFEST, contract_artifacts, CONTRACT_REVIEW_CSV, contract_rows
    )


if __name__ == "__main__":
    main()
