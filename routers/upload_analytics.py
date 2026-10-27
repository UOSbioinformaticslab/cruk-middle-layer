import json
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, Response, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db
import models
import schemas

router = APIRouter(
    prefix="/filter-modifications",
    tags=["Filter Modifications Telemetry"]
)

def truncate_snippet(snippet: Optional[str], keyword: Optional[str], window: int = 100) -> Optional[str]:
    """
    Truncates snippet strictly to +- window characters around the triggering keyword
    to safeguard confidentiality of draft metadata.
    """
    if not snippet:
        return snippet
    s = str(snippet).strip()
    if not keyword or keyword.lower() not in s.lower():
        # Fallback: keep max 200 chars
        return s[:2 * window] + ("..." if len(s) > 2 * window else "")
    
    idx = s.lower().find(keyword.lower())
    start = max(0, idx - window)
    end = min(len(s), idx + len(keyword) + window)
    
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(s) else ""
    return f"{prefix}{s[start:end].strip()}{suffix}"

_TAXONOMY_CACHE: Dict[str, Dict[str, str]] = {}

def get_taxonomy_lookup() -> Dict[str, Dict[str, str]]:
    """Loads filter canonical labels and full hierarchy paths from cruk_datahub.db."""
    global _TAXONOMY_CACHE
    if _TAXONOMY_CACHE:
        return _TAXONOMY_CACHE

    import sqlite3, os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "..", "..", "basic", "basic_backend", "cruk_datahub.db"),
        os.path.join(base_dir, "..", "cruk_datahub.db"),
        os.path.join(os.getcwd(), "basic", "basic_backend", "cruk_datahub.db"),
        os.path.join(os.getcwd(), "cruk_datahub.db")
    ]
    for db_p in candidates:
        if os.path.isfile(db_p):
            try:
                conn = sqlite3.connect(f"file:{db_p}?mode=ro", uri=True)
                c = conn.cursor()
                c.execute("SELECT id, label, path FROM filters;")
                raw = {r[0]: (r[1], json.loads(r[2]) if r[2] else []) for r in c.fetchall()}
                conn.close()

                lookup = {}
                for fid, (label, path) in raw.items():
                    clean_label = "Data Type" if label == "dataType" else (label or fid)
                    path_labels = []
                    for pid in path:
                        plabel = raw.get(pid, (pid, []))[0]
                        if plabel == "dataType":
                            plabel = "Data Type"
                        elif plabel == "cancerTypes":
                            plabel = "Cancer Type"
                        elif plabel == "accessType":
                            plabel = "Access Type"
                        path_labels.append(plabel)
                    hierarchy = " > ".join(path_labels) if path_labels else clean_label
                    lookup[fid] = {
                        "label": clean_label,
                        "hierarchy": hierarchy
                    }
                _TAXONOMY_CACHE = lookup
                return lookup
            except Exception:
                pass
    return {}

def normalize_dataset_name(name: Optional[str], dataset_id: Optional[str] = None) -> str:
    """Normalizes dataset name for display and robust deduplication."""
    if name and str(name).strip():
        return str(name).strip()
    if dataset_id and str(dataset_id).strip():
        return f"Dataset #{str(dataset_id).strip()}"
    return "Untitled Dataset"

@router.post("/session", response_model=schemas.UploadSessionResponse)
def record_upload_session(payload: schemas.UploadSessionCreate, db: Session = Depends(get_db)):
    """
    Records an upload session including recommender feedback, rejected filters, and manual additions.
    Deduplicates rejections and manual filters so that duplicate submissions for the same dataset
    name update existing events rather than polluting the database with identical duplicates.
    """
    clean_dataset_name = normalize_dataset_name(payload.dataset_name, payload.dataset_id)

    # Deduplicate payload manual filters by ID
    seen_manual_ids = set()
    deduped_manual = []
    for mf in (payload.manual_filters_added or []):
        if isinstance(mf, dict):
            fid = str(mf.get("id") or "").strip()
            if fid and fid not in seen_manual_ids:
                seen_manual_ids.add(fid)
                deduped_manual.append(mf)

    db_session = models.UploadSession(
        session_id=payload.session_id,
        dataset_id=payload.dataset_id,
        dataset_name=clean_dataset_name,
        recommender_used=payload.recommender_used,
        recommender_action=payload.recommender_action,
        total_recommended=payload.total_recommended,
        total_accepted=payload.total_accepted,
        total_rejected=payload.total_rejected,
        manual_filters_added=json.dumps(deduped_manual),
        sections_visited=json.dumps(payload.sections_visited or []),
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)

    # Check existing rejections for this dataset name (case-insensitive) to prevent duplicate event rows
    existing_rejections = db.query(models.FilterRejectionEvent).filter(
        models.FilterRejectionEvent.dataset_name.ilike(clean_dataset_name)
    ).all()
    existing_by_filter_id = {e.filter_id: e for e in existing_rejections}

    # Record rejected filter events, deduplicating incoming filters by filter_id
    seen_payload_rej_ids = set()
    for rej in (payload.rejected_filters or []):
        fid = str(rej.filter_id or "").strip()
        if not fid or fid in seen_payload_rej_ids:
            continue
        seen_payload_rej_ids.add(fid)

        # Exclude filter rejections that were suggested as a result of child filters
        if rej.metadata_field == "hierarchical_parent" or (rej.snippet_context and "Triggered automatically by child filter" in rej.snippet_context):
            continue

        cleaned_snippet = truncate_snippet(rej.snippet_context, rej.triggering_phrase, window=100)

        if fid in existing_by_filter_id:
            # Update existing rejection event rather than inserting a duplicate row
            existing_event = existing_by_filter_id[fid]
            existing_event.upload_session_id = db_session.id
            existing_event.dataset_id = payload.dataset_id or existing_event.dataset_id
            existing_event.filter_label = rej.filter_label or existing_event.filter_label
            existing_event.triggering_phrase = rej.triggering_phrase or existing_event.triggering_phrase
            existing_event.metadata_field = rej.metadata_field or existing_event.metadata_field
            existing_event.snippet_context = cleaned_snippet or existing_event.snippet_context
            existing_event.rejection_type = rej.rejection_type or existing_event.rejection_type
            existing_event.created_at = datetime.now(timezone.utc)
        else:
            rejection_event = models.FilterRejectionEvent(
                upload_session_id=db_session.id,
                dataset_id=payload.dataset_id,
                dataset_name=clean_dataset_name,
                filter_id=fid,
                filter_label=rej.filter_label,
                triggering_phrase=rej.triggering_phrase,
                metadata_field=rej.metadata_field,
                snippet_context=cleaned_snippet,
                rejection_type=rej.rejection_type or "INDIVIDUAL_DISMISS"
            )
            db.add(rejection_event)
            existing_by_filter_id[fid] = rejection_event

    db.commit()
    return db_session

@router.get("/rejections")
def get_filter_rejections(
    since: Optional[str] = Query(None, description="Start date YYYY-MM-DD (defaults to 30 days ago)"),
    filter_id: Optional[str] = Query(None, description="Optional specific filter ID to inspect, e.g. 0_0_5"),
    format: Optional[str] = Query("json", description="Response format: 'json' or 'summary_text'"),
    db: Session = Depends(get_db)
):
    """
    Answers: 'Which filters were rejected and why?'
    Groups rejections by filter ID, datasets, triggering phrases, metadata fields, and sample snippets.
    Guarantees that if the same filter is rejected for a dataset of the same name twice,
    it does not get picked up more than once. Excludes parent rejections triggered by child filters.
    """
    if since:
        try:
            since_dt = datetime.strptime(since, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    else:
        since_dt = datetime.now(timezone.utc) - timedelta(days=30)
        since = since_dt.strftime("%Y-%m-%d")

    query = db.query(models.FilterRejectionEvent).filter(
        models.FilterRejectionEvent.created_at >= since_dt,
        models.FilterRejectionEvent.metadata_field != "hierarchical_parent",
        ~models.FilterRejectionEvent.snippet_context.like("%Triggered automatically by child filter%")
    )
    if filter_id:
        query = query.filter(models.FilterRejectionEvent.filter_id == filter_id)

    # Order newest first so the most recent context/snippet is retained for each dataset
    rejections = query.order_by(desc(models.FilterRejectionEvent.created_at)).all()
    taxonomy = get_taxonomy_lookup()

    # Aggregate by filter_id
    grouped_data: Dict[str, Dict[str, Any]] = {}
    seen_filter_dataset_rejections: set = set()  # (filter_id, dataset_name_lower)
    total_deduplicated_rejections = 0

    for r in rejections:
        fid = r.filter_id
        dataset_name = normalize_dataset_name(r.dataset_name, r.dataset_id)
        dataset_key = (fid, dataset_name.strip().lower())

        # Ensure that if the same filter is rejected for a dataset of the same name twice,
        # it does not get picked up more than once.
        if dataset_key in seen_filter_dataset_rejections:
            continue
        seen_filter_dataset_rejections.add(dataset_key)
        total_deduplicated_rejections += 1

        tax_info = taxonomy.get(fid, {})
        canonical_label = tax_info.get("label") or (r.filter_label if r.filter_label and r.filter_label != fid else fid)
        hierarchy = tax_info.get("hierarchy")

        if fid not in grouped_data:
            grouped_data[fid] = {
                "filter_id": fid,
                "filter_label": canonical_label,
                "filter_hierarchy": hierarchy,
                "rejection_count": 0,
                "datasets": set(),
                "phrases": {}  # (phrase, field) -> {count, snippets}
            }
        
        entry = grouped_data[fid]
        entry["rejection_count"] += 1
        entry["datasets"].add(dataset_name)

        phrase_key = (r.triggering_phrase or "Unspecified phrase", r.metadata_field or "metadata")
        if phrase_key not in entry["phrases"]:
            entry["phrases"][phrase_key] = {
                "phrase": phrase_key[0],
                "field": phrase_key[1],
                "count": 0,
                "snippets": []
            }
        entry["phrases"][phrase_key]["count"] += 1
        if r.snippet_context and r.snippet_context not in entry["phrases"][phrase_key]["snippets"]:
            if len(entry["phrases"][phrase_key]["snippets"]) < 3:
                entry["phrases"][phrase_key]["snippets"].append(r.snippet_context)

    # Format structured output
    filter_groups: List[schemas.FilterRejectionGroup] = []
    for fid, item in sorted(grouped_data.items(), key=lambda x: x[1]["rejection_count"], reverse=True):
        phrase_summaries = [
            schemas.TriggeringPhraseSummary(
                phrase=p["phrase"],
                field=p["field"],
                count=p["count"],
                sample_snippets=p["snippets"]
            )
            for p in sorted(item["phrases"].values(), key=lambda p: p["count"], reverse=True)
        ]

        filter_groups.append(schemas.FilterRejectionGroup(
            filter_id=item["filter_id"],
            filter_label=item["filter_label"],
            filter_hierarchy=item.get("filter_hierarchy"),
            rejection_count=item["rejection_count"],
            dataset_names=sorted(list(item["datasets"])),
            triggering_phrases=phrase_summaries
        ))

    if format == "summary_text":
        lines = [f"=== Filter Rejections Summary (Since {since}) ==="]
        if not filter_groups:
            lines.append("No filter rejections recorded for this period.")
        for g in filter_groups:
            hier_str = f" [Hierarchy: {g.filter_hierarchy}]" if g.filter_hierarchy else ""
            lines.append(f"\n{g.filter_id} {g.filter_label}{hier_str}: {g.rejection_count} rejections")
            lines.append(f"Datasets ({len(g.dataset_names)}): {g.dataset_names}")
            lines.append("Triggering phrases:")
            for p in g.triggering_phrases:
                snippet_str = f' (e.g. "{p.sample_snippets[0]}")' if p.sample_snippets else ""
                lines.append(f"  - \"{p.phrase}\" in {p.field} ({p.count} times){snippet_str}")
        return Response(content="\n".join(lines), media_type="text/plain")

    return schemas.FilterRejectionsResponse(
        since=since,
        total_rejections=total_deduplicated_rejections,
        filters=filter_groups
    )

@router.get("/manual-additions", response_model=schemas.ManualFiltersResponse)
def get_manual_additions(
    since: Optional[str] = Query(None, description="Start date YYYY-MM-DD (defaults to 30 days ago)"),
    db: Session = Depends(get_db)
):
    """
    Answers: 'Which additional filters were included?'
    Aggregates filters manually added by uploaders that were not suggested by the recommender.
    Guarantees that if the same filter is added to a dataset of the same name twice,
    it does not get picked up more than once.
    """
    if since:
        try:
            since_dt = datetime.strptime(since, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    else:
        since_dt = datetime.now(timezone.utc) - timedelta(days=30)
        since = since_dt.strftime("%Y-%m-%d")

    # Order newest first
    sessions = db.query(models.UploadSession).filter(
        models.UploadSession.created_at >= since_dt
    ).order_by(desc(models.UploadSession.created_at)).all()
    taxonomy = get_taxonomy_lookup()

    manual_map: Dict[str, Dict[str, Any]] = {}
    seen_filter_dataset_additions: set = set()  # (filter_id, dataset_name_lower)
    total_deduplicated_additions = 0

    for s in sessions:
        if not s.manual_filters_added:
            continue
        dataset_name = normalize_dataset_name(s.dataset_name, s.dataset_id)
        dataset_name_lower = dataset_name.strip().lower()

        try:
            filters = json.loads(s.manual_filters_added)
            if not isinstance(filters, list):
                continue
            for f in filters:
                if not isinstance(f, dict):
                    continue
                fid = str(f.get("id") or "").strip()
                if not fid:
                    continue

                addition_key = (fid, dataset_name_lower)
                # Ensure that if the same filter is added to a dataset of the same name twice,
                # it does not get picked up more than once.
                if addition_key in seen_filter_dataset_additions:
                    continue
                seen_filter_dataset_additions.add(addition_key)
                total_deduplicated_additions += 1

                tax_info = taxonomy.get(fid, {})
                canonical_label = tax_info.get("label") or f.get("label") or fid
                hierarchy = tax_info.get("hierarchy")

                if fid not in manual_map:
                    manual_map[fid] = {
                        "filter_id": fid,
                        "filter_label": canonical_label,
                        "filter_hierarchy": hierarchy,
                        "category": f.get("category"),
                        "times_added": 0,
                        "datasets": set()
                    }
                manual_map[fid]["times_added"] += 1
                manual_map[fid]["datasets"].add(dataset_name)
        except Exception:
            continue

    sorted_manual = sorted(manual_map.values(), key=lambda x: x["times_added"], reverse=True)
    result_items = [
        schemas.ManualFilterItem(
            filter_id=m["filter_id"],
            filter_label=m["filter_label"],
            filter_hierarchy=m.get("filter_hierarchy"),
            category=m["category"],
            times_added=m["times_added"],
            datasets=sorted(list(m["datasets"]))
        )
        for m in sorted_manual
    ]

    return schemas.ManualFiltersResponse(
        since=since,
        total_manual_additions=total_deduplicated_additions,
        filters=result_items
    )

@router.delete("/reset")
def reset_filter_modifications_data(
    filter_id: Optional[str] = Query(None, description="Optional filter ID to reset individually"),
    db: Session = Depends(get_db)
):
    """
    Clears all upload sessions and filter rejection events, or resets a specific filter ID individually.
    """
    if filter_id and filter_id.strip():
        target_id = filter_id.strip()
        # 1. Delete rejection events for this specific filter_id
        db.query(models.FilterRejectionEvent).filter(
            models.FilterRejectionEvent.filter_id == target_id
        ).delete(synchronize_session=False)

        # 2. Remove this filter from manual_filters_added in all upload sessions
        sessions = db.query(models.UploadSession).all()
        for s in sessions:
            if s.manual_filters_added:
                try:
                    f_list = json.loads(s.manual_filters_added)
                    if isinstance(f_list, list):
                        updated = [f for f in f_list if isinstance(f, dict) and str(f.get("id") or "").strip() != target_id]
                        if len(updated) != len(f_list):
                            s.manual_filters_added = json.dumps(updated)
                except Exception:
                    pass
        db.commit()
        return {"status": "success", "message": f"Telemetry for filter '{target_id}' reset successfully."}

    # Full reset across all telemetry
    db.query(models.FilterRejectionEvent).delete()
    db.query(models.UploadSession).delete()
    db.commit()
    return {"status": "success", "message": "All upload sessions and rejection telemetry cleared."}

@router.delete("/filters/{filter_id}")
def reset_single_filter(filter_id: str, db: Session = Depends(get_db)):
    """Convenience REST endpoint to reset a single filter's telemetry."""
    return reset_filter_modifications_data(filter_id=filter_id, db=db)

def find_filter_rule(filter_id: str) -> Dict[str, Any]:
    """
    Searches filter_rules.json for any rule definitions that map to the given filter_id.
    """
    import os, json
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "..", "..", "basic", "basic_backend", "helpers", "filter_rules.json"),
        os.path.join(base_dir, "..", "helpers", "filter_rules.json"),
        os.path.join(os.getcwd(), "basic", "basic_backend", "helpers", "filter_rules.json"),
        os.path.join(os.getcwd(), "helpers", "filter_rules.json"),
        os.path.join(os.getcwd(), "filter_rules.json"),
    ]
    rules_path = None
    for p in candidates:
        if os.path.isfile(p):
            rules_path = p
            break
    if not rules_path:
        return {"filter_id": filter_id, "matched_rules": [], "parent_rule": None, "source_file": None}

    try:
        with open(rules_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {"filter_id": filter_id, "matched_rules": [], "parent_rule": None, "source_file": None}

    clean_id = filter_id.strip()
    rule_sections = [
        "topography_rules",
        "histology_rules",
        "data_type_rules",
        "parent_category_rules",
        "access_rules"
    ]
    matched_rules = []
    for sec in rule_sections:
        for r in data.get(sec, []):
            fids = r.get("filter_ids") or ([r.get("filter_id")] if r.get("filter_id") else [])
            if clean_id in [str(x).strip() for x in fids]:
                matched_rules.append({"section": sec, "rule": r})

    # Check hierarchy for parent rule if direct rule not found or to supplement
    hierarchy = data.get("hierarchy", {})
    parent_id = hierarchy.get(clean_id)
    parent_rule = None
    if parent_id:
        for sec in rule_sections:
            for r in data.get(sec, []):
                fids = r.get("filter_ids") or ([r.get("filter_id")] if r.get("filter_id") else [])
                if str(parent_id).strip() in [str(x).strip() for x in fids]:
                    parent_rule = {"section": sec, "rule": r, "parent_id": parent_id}
                    break
            if parent_rule:
                break

    return {
        "filter_id": clean_id,
        "matched_rules": matched_rules,
        "parent_rule": parent_rule,
        "source_file": "basic/basic_backend/helpers/filter_rules.json"
    }

@router.get("/filter-rule")
def get_filter_rule_endpoint(
    filter_id: str = Query(..., description="Filter ID to look up in filter_rules.json")
):
    """
    Looks up and returns the exact rule definition(s) from filter_rules.json matching the given filter ID.
    """
    return find_filter_rule(filter_id)

@router.get("/dataset-metadata")
def get_dataset_metadata(
    name: Optional[str] = Query(None, description="Dataset title or name"),
    dataset_id: Optional[str] = Query(None, description="Optional dataset integer ID or datasetid string"),
    filter_id: Optional[str] = Query(None, description="Optional filter ID to look up rule snippet in filter_rules.json")
):
    """
    Returns full metadata, assigned filters, text corpus, and filter rule definition for a specific dataset
    to power the Slide-out Dataset Metadata Drawer.
    """
    if not name and not dataset_id:
        raise HTTPException(status_code=400, detail="Must provide either name or dataset_id parameter.")

    import sqlite3, os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "..", "..", "basic", "basic_backend", "cruk_datahub.db"),
        os.path.join(base_dir, "..", "cruk_datahub.db"),
        os.path.join(os.getcwd(), "basic", "basic_backend", "cruk_datahub.db"),
        os.path.join(os.getcwd(), "cruk_datahub.db")
    ]
    
    db_path = None
    for p in candidates:
        if os.path.isfile(p):
            db_path = p
            break
            
    if not db_path:
        raise HTTPException(status_code=500, detail="cruk_datahub.db not found on server.")

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    c = conn.cursor()
    c.execute("SELECT id, datasetid, metadata_blob FROM datasets;")
    rows = c.fetchall()
    conn.close()

    target_name = (name or "").strip().lower()
    target_id = str(dataset_id or "").strip().lower()

    matched_row = None
    for r in rows:
        db_id = str(r[0])
        db_datasetid = str(r[1] or "")
        blob = json.loads(r[2]) if r[2] else {}
        db_title = (blob.get("summary", {}).get("title") or blob.get("name") or f"Dataset #{db_id}").strip()

        # Match logic
        if target_id and (target_id == db_id.lower() or target_id == db_datasetid.lower()):
            matched_row = (r[0], r[1], blob, db_title)
            break
        if target_name:
            if target_name == db_title.lower():
                matched_row = (r[0], r[1], blob, db_title)
                break
            if target_name in db_title.lower() or db_title.lower() in target_name:
                matched_row = (r[0], r[1], blob, db_title)
                break

    if not matched_row:
        raise HTTPException(status_code=404, detail=f"Dataset '{name or dataset_id}' not found.")

    ds_id, ds_datasetid, metadata, ds_title = matched_row
    summary = metadata.get("summary", {}) or {}
    documentation = metadata.get("documentation", {}) or {}
    accessibility = metadata.get("accessibility", {}) or {}
    access = accessibility.get("access", {}) or {}
    pg = metadata.get("projectGrant", {}) or {}

    abstract = summary.get("abstract", "") or metadata.get("abstract", "") or ""
    keywords = summary.get("keywords", []) or metadata.get("keywords", []) or []
    description = documentation.get("description", "") or metadata.get("description", "") or ""
    researcher = summary.get("leadResearcher") or pg.get("leadResearcher") or metadata.get("leadResearcher") or ""
    institute = summary.get("leadResearchInstitute") or pg.get("leadResearchInstitute") or metadata.get("leadResearchInstitute") or ""
    access_rights = access.get("accessRights", "") or ""

    # Build combined corpus
    full_text = f"{ds_title} {abstract} {' '.join(str(k) for k in keywords)} {description} {access_rights}".strip()

    filters = metadata.get("datasetFilters", []) or []

    # Optional rule info lookup
    rule_info = find_filter_rule(filter_id) if filter_id else None

    return {
        "id": ds_id,
        "datasetid": ds_datasetid,
        "title": ds_title,
        "abstract": abstract,
        "keywords": keywords,
        "description": description,
        "lead_researcher": researcher,
        "lead_institute": institute,
        "access_rights": access_rights,
        "filters": filters,
        "full_text": full_text,
        "rule_info": rule_info
    }
