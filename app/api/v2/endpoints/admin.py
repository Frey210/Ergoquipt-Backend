from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date
import uuid
import io
import csv
import json
import zipfile
import re

from app.database.database import get_db
from app.core.auth import require_admin, require_web_platform
from app.database.models import (
    HrvBulkRecording,
    HrvBulkReading,
    TympaniBulkRecording,
    TympaniBulkReading,
    User,
    UserRole,
)
from app.schemas.tympani_bulk import TympaniBulkDownloadRequest
from app.schemas.hrv_bulk import HrvBulkDownloadRequest

router = APIRouter()

def _build_label(name: str, time_start: datetime, time_end: datetime) -> str:
    return f"{name}_{time_start.isoformat()}-{time_end.isoformat()}"

def _sanitize_filename(label: str, extension: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", label).strip("_")
    if not safe:
        safe = "recording"
    return f"{safe}.{extension}"

def _operator_scope(
    db: Session,
    admin: User,
    operator_id: Optional[str],
) -> Tuple[Dict[uuid.UUID, str], List[uuid.UUID]]:
    query = db.query(User).filter(User.role == UserRole.OPERATOR)
    if admin.role != UserRole.SUPER_ADMIN:
        query = query.filter(User.created_by == admin.id)

    if operator_id:
        try:
            operator_uuid = uuid.UUID(operator_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid operator_id")
        query = query.filter(User.id == operator_uuid)

    operators = query.all()
    if operator_id and not operators:
        raise HTTPException(status_code=404, detail="Operator not found")

    operator_map = {operator.id: operator.full_name for operator in operators}
    operator_ids = list(operator_map.keys())
    return operator_map, operator_ids

def _recording_to_csv_tympani(
    recording: TympaniBulkRecording,
    readings: List[TympaniBulkReading],
) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "recording_id",
        "label",
        "operator_id",
        "respondent_local_id",
        "respondent_name",
        "respondent_age",
        "respondent_gender",
        "respondent_height",
        "respondent_weight",
        "respondent_created_at",
        "time_start",
        "time_end",
        "recorded_at",
        "value",
    ])
    for reading in readings:
        writer.writerow([
            str(recording.id),
            recording.label,
            str(recording.operator_id),
            recording.respondent_local_id or "",
            recording.respondent_name,
            recording.respondent_age or "",
            recording.respondent_gender or "",
            recording.respondent_height or "",
            recording.respondent_weight or "",
            recording.respondent_created_at.isoformat() if recording.respondent_created_at else "",
            recording.time_start.isoformat(),
            recording.time_end.isoformat(),
            reading.recorded_at.isoformat(),
            float(reading.value),
        ])
    output.seek(0)
    return output.getvalue()

def _recording_to_json_tympani(
    recording: TympaniBulkRecording,
    readings: List[TympaniBulkReading],
) -> str:
    payload = {
        "recording": {
            "id": str(recording.id),
            "label": recording.label,
            "operator_id": str(recording.operator_id),
            "respondent": {
                "local_id": recording.respondent_local_id,
                "name": recording.respondent_name,
                "age": recording.respondent_age,
                "gender": recording.respondent_gender,
                "height": recording.respondent_height,
                "weight": recording.respondent_weight,
                "created_at": recording.respondent_created_at.isoformat() if recording.respondent_created_at else None,
            },
            "time_start": recording.time_start.isoformat(),
            "time_end": recording.time_end.isoformat(),
            "created_at": recording.created_at.isoformat() if recording.created_at else None,
        },
        "readings": [
            {
                "value": float(reading.value),
                "recorded_at": reading.recorded_at.isoformat(),
            }
            for reading in readings
        ],
    }
    return json.dumps(payload, ensure_ascii=False)

def _recording_to_csv_hrv(
    recording: HrvBulkRecording,
    readings: List[HrvBulkReading],
) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "recording_id",
        "label",
        "operator_id",
        "respondent_local_id",
        "respondent_name",
        "respondent_age",
        "respondent_gender",
        "respondent_height",
        "respondent_weight",
        "respondent_created_at",
        "time_start",
        "time_end",
        "recorded_at",
        "heart_rate",
        "rr_interval",
        "spo2",
    ])
    for reading in readings:
        writer.writerow([
            str(recording.id),
            recording.label,
            str(recording.operator_id),
            recording.respondent_local_id or "",
            recording.respondent_name,
            recording.respondent_age or "",
            recording.respondent_gender or "",
            recording.respondent_height or "",
            recording.respondent_weight or "",
            recording.respondent_created_at.isoformat() if recording.respondent_created_at else "",
            recording.time_start.isoformat(),
            recording.time_end.isoformat(),
            reading.recorded_at.isoformat(),
            reading.heart_rate if reading.heart_rate is not None else "",
            float(reading.rr_interval) if reading.rr_interval is not None else "",
            float(reading.spo2) if reading.spo2 is not None else "",
        ])
    output.seek(0)
    return output.getvalue()

def _recording_to_json_hrv(
    recording: HrvBulkRecording,
    readings: List[HrvBulkReading],
) -> str:
    payload = {
        "recording": {
            "id": str(recording.id),
            "label": recording.label,
            "operator_id": str(recording.operator_id),
            "respondent": {
                "local_id": recording.respondent_local_id,
                "name": recording.respondent_name,
                "age": recording.respondent_age,
                "gender": recording.respondent_gender,
                "height": recording.respondent_height,
                "weight": recording.respondent_weight,
                "created_at": recording.respondent_created_at.isoformat() if recording.respondent_created_at else None,
            },
            "time_start": recording.time_start.isoformat(),
            "time_end": recording.time_end.isoformat(),
            "created_at": recording.created_at.isoformat() if recording.created_at else None,
        },
        "readings": [
            {
                "heart_rate": reading.heart_rate,
                "rr_interval": float(reading.rr_interval) if reading.rr_interval is not None else None,
                "spo2": float(reading.spo2) if reading.spo2 is not None else None,
                "recorded_at": reading.recorded_at.isoformat(),
            }
            for reading in readings
        ],
    }
    return json.dumps(payload, ensure_ascii=False)

def _parse_group_by(group_by: str) -> str:
    if group_by not in ["day", "week", "month"]:
        raise HTTPException(status_code=400, detail="group_by must be day, week, or month")
    return group_by

def _period_key(dt: datetime, group_by: str) -> str:
    if group_by == "day":
        return dt.date().isoformat()
    if group_by == "week":
        year, week, _ = dt.date().isocalendar()
        return f"{year}-W{week:02d}"
    return f"{dt.year}-{dt.month:02d}"

def _timeseries_from_datetimes(
    datetimes: List[datetime],
    group_by: str,
) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for dt in datetimes:
        key = _period_key(dt, group_by)
        counts[key] = counts.get(key, 0) + 1
    return counts

@router.get("/tympani/recordings")
async def list_tympani_recordings_admin(
    operator_id: Optional[str] = Query(None),
    from_time: Optional[datetime] = Query(None),
    to_time: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    platform_check: User = Depends(require_web_platform),
):
    operator_map, operator_ids = _operator_scope(db, admin, operator_id)
    if not operator_ids:
        return {"items": [], "total": 0}

    query = db.query(TympaniBulkRecording).filter(TympaniBulkRecording.operator_id.in_(operator_ids))
    if from_time:
        query = query.filter(TympaniBulkRecording.time_start >= from_time)
    if to_time:
        query = query.filter(TympaniBulkRecording.time_end <= to_time)

    total = query.count()
    recordings = query.order_by(TympaniBulkRecording.created_at.desc()).offset(offset).limit(limit).all()

    recording_ids = [recording.id for recording in recordings]
    counts = {}
    if recording_ids:
        counts = dict(
            db.query(TympaniBulkReading.recording_id, func.count(TympaniBulkReading.id))
            .filter(TympaniBulkReading.recording_id.in_(recording_ids))
            .group_by(TympaniBulkReading.recording_id)
            .all()
        )

    items = []
    for recording in recordings:
        items.append(
            {
                "id": str(recording.id),
                "label": recording.label,
                "operator_id": str(recording.operator_id),
                "operator_name": operator_map.get(recording.operator_id, ""),
                "respondent": {
                    "local_id": recording.respondent_local_id,
                    "name": recording.respondent_name,
                    "age": recording.respondent_age,
                    "gender": recording.respondent_gender,
                    "height": recording.respondent_height,
                    "weight": recording.respondent_weight,
                    "created_at": recording.respondent_created_at,
                },
                "time_start": recording.time_start,
                "time_end": recording.time_end,
                "count": counts.get(recording.id, 0),
                "created_at": recording.created_at,
            }
        )

    return {"items": items, "total": total}

@router.get("/tympani/recordings/{recording_id}/download")
async def download_tympani_recording_admin(
    recording_id: str,
    format: str = Query("csv"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    platform_check: User = Depends(require_web_platform),
):
    if format not in ["csv", "json"]:
        raise HTTPException(status_code=400, detail="format must be csv or json")

    try:
        recording_uuid = uuid.UUID(recording_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid recording_id")

    _, operator_ids = _operator_scope(db, admin, None)
    recording = db.query(TympaniBulkRecording).filter(
        TympaniBulkRecording.id == recording_uuid,
        TympaniBulkRecording.operator_id.in_(operator_ids),
    ).first()

    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    readings = db.query(TympaniBulkReading).filter(
        TympaniBulkReading.recording_id == recording.id
    ).order_by(TympaniBulkReading.recorded_at).all()

    if format == "csv":
        payload = _recording_to_csv_tympani(recording, readings)
        filename = _sanitize_filename(recording.label, "csv")
        return StreamingResponse(
            iter([payload]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    payload = _recording_to_json_tympani(recording, readings)
    filename = _sanitize_filename(recording.label, "json")
    return StreamingResponse(
        iter([payload]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

@router.post("/tympani/recordings/download")
async def download_tympani_recordings_bulk_admin(
    payload: TympaniBulkDownloadRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    platform_check: User = Depends(require_web_platform),
):
    recording_ids = payload.recording_ids
    if payload.format not in ["csv", "json"]:
        raise HTTPException(status_code=400, detail="format must be csv or json")
    if not recording_ids:
        raise HTTPException(status_code=400, detail="recording_ids must not be empty")

    try:
        recording_uuids = [uuid.UUID(recording_id) for recording_id in recording_ids]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid recording_id in list")

    _, operator_ids = _operator_scope(db, admin, None)
    recordings = db.query(TympaniBulkRecording).filter(
        TympaniBulkRecording.operator_id.in_(operator_ids),
        TympaniBulkRecording.id.in_(recording_uuids),
    ).all()

    recordings_by_id = {recording.id: recording for recording in recordings}
    missing_ids = [recording_id for recording_id in recording_uuids if recording_id not in recordings_by_id]
    if missing_ids:
        missing_str = [str(recording_id) for recording_id in missing_ids]
        raise HTTPException(status_code=404, detail={"missing_recordings": missing_str})

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for recording_id in recording_uuids:
            recording = recordings_by_id[recording_id]
            readings = db.query(TympaniBulkReading).filter(
                TympaniBulkReading.recording_id == recording.id
            ).order_by(TympaniBulkReading.recorded_at).all()

            if payload.format == "csv":
                content = _recording_to_csv_tympani(recording, readings)
                filename = _sanitize_filename(recording.label, "csv")
            else:
                content = _recording_to_json_tympani(recording, readings)
                filename = _sanitize_filename(recording.label, "json")

            zip_file.writestr(filename, content)

    zip_buffer.seek(0)
    filename = f"tympani_recordings_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip"
    return StreamingResponse(
        iter([zip_buffer.getvalue()]),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

@router.get("/hrv/recordings")
async def list_hrv_recordings_admin(
    operator_id: Optional[str] = Query(None),
    from_time: Optional[datetime] = Query(None),
    to_time: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    platform_check: User = Depends(require_web_platform),
):
    operator_map, operator_ids = _operator_scope(db, admin, operator_id)
    if not operator_ids:
        return {"items": [], "total": 0}

    query = db.query(HrvBulkRecording).filter(HrvBulkRecording.operator_id.in_(operator_ids))
    if from_time:
        query = query.filter(HrvBulkRecording.time_start >= from_time)
    if to_time:
        query = query.filter(HrvBulkRecording.time_end <= to_time)

    total = query.count()
    recordings = query.order_by(HrvBulkRecording.created_at.desc()).offset(offset).limit(limit).all()

    recording_ids = [recording.id for recording in recordings]
    counts = {}
    if recording_ids:
        counts = dict(
            db.query(HrvBulkReading.recording_id, func.count(HrvBulkReading.id))
            .filter(HrvBulkReading.recording_id.in_(recording_ids))
            .group_by(HrvBulkReading.recording_id)
            .all()
        )

    items = []
    for recording in recordings:
        items.append(
            {
                "id": str(recording.id),
                "label": recording.label,
                "operator_id": str(recording.operator_id),
                "operator_name": operator_map.get(recording.operator_id, ""),
                "respondent": {
                    "local_id": recording.respondent_local_id,
                    "name": recording.respondent_name,
                    "age": recording.respondent_age,
                    "gender": recording.respondent_gender,
                    "height": recording.respondent_height,
                    "weight": recording.respondent_weight,
                    "created_at": recording.respondent_created_at,
                },
                "time_start": recording.time_start,
                "time_end": recording.time_end,
                "count": counts.get(recording.id, 0),
                "created_at": recording.created_at,
            }
        )

    return {"items": items, "total": total}

@router.get("/hrv/recordings/{recording_id}/download")
async def download_hrv_recording_admin(
    recording_id: str,
    format: str = Query("csv"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    platform_check: User = Depends(require_web_platform),
):
    if format not in ["csv", "json"]:
        raise HTTPException(status_code=400, detail="format must be csv or json")

    try:
        recording_uuid = uuid.UUID(recording_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid recording_id")

    _, operator_ids = _operator_scope(db, admin, None)
    recording = db.query(HrvBulkRecording).filter(
        HrvBulkRecording.id == recording_uuid,
        HrvBulkRecording.operator_id.in_(operator_ids),
    ).first()

    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    readings = db.query(HrvBulkReading).filter(
        HrvBulkReading.recording_id == recording.id
    ).order_by(HrvBulkReading.recorded_at).all()

    if format == "csv":
        payload = _recording_to_csv_hrv(recording, readings)
        filename = _sanitize_filename(recording.label, "csv")
        return StreamingResponse(
            iter([payload]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    payload = _recording_to_json_hrv(recording, readings)
    filename = _sanitize_filename(recording.label, "json")
    return StreamingResponse(
        iter([payload]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

@router.post("/hrv/recordings/download")
async def download_hrv_recordings_bulk_admin(
    payload: HrvBulkDownloadRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    platform_check: User = Depends(require_web_platform),
):
    recording_ids = payload.recording_ids
    if payload.format not in ["csv", "json"]:
        raise HTTPException(status_code=400, detail="format must be csv or json")
    if not recording_ids:
        raise HTTPException(status_code=400, detail="recording_ids must not be empty")

    try:
        recording_uuids = [uuid.UUID(recording_id) for recording_id in recording_ids]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid recording_id in list")

    _, operator_ids = _operator_scope(db, admin, None)
    recordings = db.query(HrvBulkRecording).filter(
        HrvBulkRecording.operator_id.in_(operator_ids),
        HrvBulkRecording.id.in_(recording_uuids),
    ).all()

    recordings_by_id = {recording.id: recording for recording in recordings}
    missing_ids = [recording_id for recording_id in recording_uuids if recording_id not in recordings_by_id]
    if missing_ids:
        missing_str = [str(recording_id) for recording_id in missing_ids]
        raise HTTPException(status_code=404, detail={"missing_recordings": missing_str})

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for recording_id in recording_uuids:
            recording = recordings_by_id[recording_id]
            readings = db.query(HrvBulkReading).filter(
                HrvBulkReading.recording_id == recording.id
            ).order_by(HrvBulkReading.recorded_at).all()

            if payload.format == "csv":
                content = _recording_to_csv_hrv(recording, readings)
                filename = _sanitize_filename(recording.label, "csv")
            else:
                content = _recording_to_json_hrv(recording, readings)
                filename = _sanitize_filename(recording.label, "json")

            zip_file.writestr(filename, content)

    zip_buffer.seek(0)
    filename = f"hrv_recordings_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip"
    return StreamingResponse(
        iter([zip_buffer.getvalue()]),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

@router.get("/summary/operators")
async def summary_by_operator(
    from_time: datetime = Query(...),
    to_time: datetime = Query(...),
    operator_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    platform_check: User = Depends(require_web_platform),
):
    operator_map, operator_ids = _operator_scope(db, admin, operator_id)
    if not operator_ids:
        return {"items": []}

    tympani_counts = dict(
        db.query(TympaniBulkRecording.operator_id, func.count(TympaniBulkRecording.id))
        .filter(
            TympaniBulkRecording.operator_id.in_(operator_ids),
            TympaniBulkRecording.time_start >= from_time,
            TympaniBulkRecording.time_end <= to_time,
        )
        .group_by(TympaniBulkRecording.operator_id)
        .all()
    )
    hrv_counts = dict(
        db.query(HrvBulkRecording.operator_id, func.count(HrvBulkRecording.id))
        .filter(
            HrvBulkRecording.operator_id.in_(operator_ids),
            HrvBulkRecording.time_start >= from_time,
            HrvBulkRecording.time_end <= to_time,
        )
        .group_by(HrvBulkRecording.operator_id)
        .all()
    )

    items = []
    for operator_uuid in operator_ids:
        items.append(
            {
                "operator_id": str(operator_uuid),
                "operator_name": operator_map.get(operator_uuid, ""),
                "tympani_count": int(tympani_counts.get(operator_uuid, 0)),
                "hrv_count": int(hrv_counts.get(operator_uuid, 0)),
            }
        )

    return {
        "range": {"from": from_time, "to": to_time},
        "items": items,
    }

@router.get("/summary/timeseries")
async def summary_timeseries(
    from_time: datetime = Query(...),
    to_time: datetime = Query(...),
    group_by: str = Query("day"),
    metric: str = Query("both"),
    operator_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    platform_check: User = Depends(require_web_platform),
):
    group_by = _parse_group_by(group_by)
    if metric not in ["tympani", "hrv", "both"]:
        raise HTTPException(status_code=400, detail="metric must be tympani, hrv, or both")

    operator_map, operator_ids = _operator_scope(db, admin, operator_id)
    if not operator_ids:
        return {"series": [], "group_by": group_by}

    tympani_datetimes: List[datetime] = []
    hrv_datetimes: List[datetime] = []

    if metric in ["tympani", "both"]:
        tympani_datetimes = [
            row[0]
            for row in db.query(TympaniBulkRecording.time_start)
            .filter(
                TympaniBulkRecording.operator_id.in_(operator_ids),
                TympaniBulkRecording.time_start >= from_time,
                TympaniBulkRecording.time_end <= to_time,
            )
            .all()
        ]

    if metric in ["hrv", "both"]:
        hrv_datetimes = [
            row[0]
            for row in db.query(HrvBulkRecording.time_start)
            .filter(
                HrvBulkRecording.operator_id.in_(operator_ids),
                HrvBulkRecording.time_start >= from_time,
                HrvBulkRecording.time_end <= to_time,
            )
            .all()
        ]

    tympani_counts = _timeseries_from_datetimes(tympani_datetimes, group_by) if tympani_datetimes else {}
    hrv_counts = _timeseries_from_datetimes(hrv_datetimes, group_by) if hrv_datetimes else {}

    periods = sorted(set(list(tympani_counts.keys()) + list(hrv_counts.keys())))
    series = []
    for period in periods:
        series.append(
            {
                "period": period,
                "tympani_count": int(tympani_counts.get(period, 0)),
                "hrv_count": int(hrv_counts.get(period, 0)),
            }
        )

    return {
        "range": {"from": from_time, "to": to_time},
        "group_by": group_by,
        "series": series,
    }

@router.get("/summary/global")
async def summary_global(
    from_time: datetime = Query(...),
    to_time: datetime = Query(...),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    platform_check: User = Depends(require_web_platform),
):
    _, operator_ids = _operator_scope(db, admin, None)
    if not operator_ids:
        return {"tympani_count": 0, "hrv_count": 0, "operators_active": 0}

    tympani_count = db.query(func.count(TympaniBulkRecording.id)).filter(
        TympaniBulkRecording.operator_id.in_(operator_ids),
        TympaniBulkRecording.time_start >= from_time,
        TympaniBulkRecording.time_end <= to_time,
    ).scalar()
    hrv_count = db.query(func.count(HrvBulkRecording.id)).filter(
        HrvBulkRecording.operator_id.in_(operator_ids),
        HrvBulkRecording.time_start >= from_time,
        HrvBulkRecording.time_end <= to_time,
    ).scalar()

    operators_tympani = db.query(TympaniBulkRecording.operator_id).filter(
        TympaniBulkRecording.operator_id.in_(operator_ids),
        TympaniBulkRecording.time_start >= from_time,
        TympaniBulkRecording.time_end <= to_time,
    ).distinct().all()
    operators_hrv = db.query(HrvBulkRecording.operator_id).filter(
        HrvBulkRecording.operator_id.in_(operator_ids),
        HrvBulkRecording.time_start >= from_time,
        HrvBulkRecording.time_end <= to_time,
    ).distinct().all()

    active_ids = {row[0] for row in operators_tympani} | {row[0] for row in operators_hrv}

    return {
        "range": {"from": from_time, "to": to_time},
        "tympani_count": int(tympani_count or 0),
        "hrv_count": int(hrv_count or 0),
        "operators_active": len(active_ids),
    }

@router.get("/summary/export.csv")
async def summary_export_csv(
    from_time: datetime = Query(...),
    to_time: datetime = Query(...),
    group_by: str = Query("day"),
    metric: str = Query("both"),
    operator_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    platform_check: User = Depends(require_web_platform),
):
    group_by = _parse_group_by(group_by)
    if metric not in ["tympani", "hrv", "both"]:
        raise HTTPException(status_code=400, detail="metric must be tympani, hrv, or both")

    _, operator_ids = _operator_scope(db, admin, operator_id)
    if not operator_ids:
        return StreamingResponse(
            iter(["period,tympani_count,hrv_count\n"]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=summary.csv"},
        )

    tympani_datetimes: List[datetime] = []
    hrv_datetimes: List[datetime] = []
    if metric in ["tympani", "both"]:
        tympani_datetimes = [
            row[0]
            for row in db.query(TympaniBulkRecording.time_start)
            .filter(
                TympaniBulkRecording.operator_id.in_(operator_ids),
                TympaniBulkRecording.time_start >= from_time,
                TympaniBulkRecording.time_end <= to_time,
            )
            .all()
        ]
    if metric in ["hrv", "both"]:
        hrv_datetimes = [
            row[0]
            for row in db.query(HrvBulkRecording.time_start)
            .filter(
                HrvBulkRecording.operator_id.in_(operator_ids),
                HrvBulkRecording.time_start >= from_time,
                HrvBulkRecording.time_end <= to_time,
            )
            .all()
        ]

    tympani_counts = _timeseries_from_datetimes(tympani_datetimes, group_by) if tympani_datetimes else {}
    hrv_counts = _timeseries_from_datetimes(hrv_datetimes, group_by) if hrv_datetimes else {}

    periods = sorted(set(list(tympani_counts.keys()) + list(hrv_counts.keys())))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["period", "tympani_count", "hrv_count"])
    for period in periods:
        writer.writerow([
            period,
            int(tympani_counts.get(period, 0)),
            int(hrv_counts.get(period, 0)),
        ])
    output.seek(0)

    filename = f"summary_{group_by}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
