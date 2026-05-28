from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
import uuid
import io
import csv
import json
import zipfile
import re

from app.database.database import get_db
from app.core.auth import get_current_user, require_mobile_platform
from app.database.models import HrvBulkRecording, HrvBulkReading, User
from app.schemas.hrv_bulk import (
    HrvBulkCreate,
    HrvBulkCreateResponse,
    HrvBulkListResponse,
    HrvBulkDownloadRequest,
    RespondentSnapshot,
)

router = APIRouter()

HRV_METRICS = {
    "hr": ("heart_rate", "heart_rate"),
    "heart_rate": ("heart_rate", "heart_rate"),
    "rr": ("rr_interval", "rr_interval"),
    "rr_interval": ("rr_interval", "rr_interval"),
    "spo2": ("spo2", "spo2"),
    "hrv": ("hrv", "hrv"),
}
DEFAULT_HRV_METRICS = ["heart_rate", "rr_interval", "spo2", "hrv"]

def _build_label(name: str, time_start: datetime, time_end: datetime) -> str:
    return f"{name}_{time_start.isoformat()}-{time_end.isoformat()}"

def _sanitize_filename(label: str, extension: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", label).strip("_")
    if not safe:
        safe = "recording"
    return f"{safe}.{extension}"

def _parse_metrics(metrics: Optional[List[str]]) -> List[str]:
    if not metrics:
        return DEFAULT_HRV_METRICS

    selected = []
    for metric in metrics:
        for raw_value in metric.split(","):
            value = raw_value.strip().lower()
            if not value:
                continue
            if value in ["all", "all_metrics", "all metrics"]:
                return DEFAULT_HRV_METRICS
            if value not in HRV_METRICS:
                raise HTTPException(
                    status_code=400,
                    detail="metrics must contain only all, hr, rr, spo2, or hrv",
                )
            _, column_name = HRV_METRICS[value]
            if column_name not in selected:
                selected.append(column_name)

    if not selected:
        raise HTTPException(status_code=400, detail="metrics must not be empty")

    return selected

def _metric_value(reading: HrvBulkReading, metric: str):
    value = getattr(reading, metric)
    if value is None:
        return None
    if metric == "heart_rate":
        return value
    return float(value)

def _recording_to_csv(
    recording: HrvBulkRecording,
    readings: List[HrvBulkReading],
    metrics: List[str],
) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    base_headers = [
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
    ]
    writer.writerow(base_headers + metrics)
    for reading in readings:
        base_values = [
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
        ]
        metric_values = [
            _metric_value(reading, metric) if _metric_value(reading, metric) is not None else ""
            for metric in metrics
        ]
        writer.writerow(base_values + metric_values)
    output.seek(0)
    return output.getvalue()

def _recording_to_json(
    recording: HrvBulkRecording,
    readings: List[HrvBulkReading],
    metrics: List[str],
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
                **{metric: _metric_value(reading, metric) for metric in metrics},
                "recorded_at": reading.recorded_at.isoformat(),
            }
            for reading in readings
        ],
    }
    return json.dumps(payload, ensure_ascii=False)

@router.post("/recordings", response_model=HrvBulkCreateResponse)
async def create_hrv_recording(
    payload: HrvBulkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    platform_check: User = Depends(require_mobile_platform),
):
    if not payload.readings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="readings must not be empty",
        )

    if payload.time_end < payload.time_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="time_end must be after time_start",
        )

    label = _build_label(payload.respondent.name, payload.time_start, payload.time_end)

    recording = HrvBulkRecording(
        operator_id=current_user.id,
        respondent_local_id=payload.respondent.local_id,
        respondent_name=payload.respondent.name,
        respondent_age=payload.respondent.age,
        respondent_gender=payload.respondent.gender,
        respondent_height=payload.respondent.height,
        respondent_weight=payload.respondent.weight,
        respondent_created_at=payload.respondent.created_at,
        label=label,
        time_start=payload.time_start,
        time_end=payload.time_end,
    )

    db.add(recording)
    db.flush()

    readings = [
        HrvBulkReading(
            recording_id=recording.id,
            heart_rate=reading.heart_rate,
            rr_interval=reading.rr_interval,
            hrv=reading.hrv,
            spo2=reading.spo2,
            recorded_at=reading.recorded_at,
        )
        for reading in payload.readings
    ]
    db.add_all(readings)
    db.commit()

    return HrvBulkCreateResponse(
        recording_id=str(recording.id),
        label=label,
        count=len(readings),
    )

@router.get("/recordings", response_model=HrvBulkListResponse)
async def list_hrv_recordings(
    from_time: Optional[datetime] = Query(None),
    to_time: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    platform_check: User = Depends(require_mobile_platform),
):
    query = db.query(HrvBulkRecording).filter(HrvBulkRecording.operator_id == current_user.id)

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
                "respondent": RespondentSnapshot(
                    local_id=recording.respondent_local_id,
                    name=recording.respondent_name,
                    age=recording.respondent_age,
                    gender=recording.respondent_gender,
                    height=recording.respondent_height,
                    weight=recording.respondent_weight,
                    created_at=recording.respondent_created_at,
                ),
                "time_start": recording.time_start,
                "time_end": recording.time_end,
                "count": counts.get(recording.id, 0),
                "created_at": recording.created_at,
            }
        )

    return {"items": items, "total": total}

@router.get("/recordings/{recording_id}/download")
async def download_hrv_recording(
    recording_id: str,
    format: str = Query("csv"),
    metrics: Optional[List[str]] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    platform_check: User = Depends(require_mobile_platform),
):
    if format not in ["csv", "json"]:
        raise HTTPException(status_code=400, detail="format must be csv or json")
    selected_metrics = _parse_metrics(metrics)

    try:
        recording_uuid = uuid.UUID(recording_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid recording_id")

    recording = db.query(HrvBulkRecording).filter(
        HrvBulkRecording.id == recording_uuid,
        HrvBulkRecording.operator_id == current_user.id,
    ).first()

    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    readings = db.query(HrvBulkReading).filter(
        HrvBulkReading.recording_id == recording.id
    ).order_by(HrvBulkReading.recorded_at).all()

    if format == "csv":
        payload = _recording_to_csv(recording, readings, selected_metrics)
        filename = _sanitize_filename(recording.label, "csv")
        return StreamingResponse(
            iter([payload]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    payload = _recording_to_json(recording, readings, selected_metrics)
    filename = _sanitize_filename(recording.label, "json")
    return StreamingResponse(
        iter([payload]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

@router.post("/recordings/download")
async def download_hrv_recordings_bulk(
    payload: HrvBulkDownloadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    platform_check: User = Depends(require_mobile_platform),
):
    if payload.format not in ["csv", "json"]:
        raise HTTPException(status_code=400, detail="format must be csv or json")
    selected_metrics = _parse_metrics(payload.metrics)

    if not payload.recording_ids:
        raise HTTPException(status_code=400, detail="recording_ids must not be empty")

    try:
        recording_uuids = [uuid.UUID(recording_id) for recording_id in payload.recording_ids]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid recording_id in list")

    recordings = db.query(HrvBulkRecording).filter(
        HrvBulkRecording.operator_id == current_user.id,
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
                content = _recording_to_csv(recording, readings, selected_metrics)
                filename = _sanitize_filename(recording.label, "csv")
            else:
                content = _recording_to_json(recording, readings, selected_metrics)
                filename = _sanitize_filename(recording.label, "json")

            zip_file.writestr(filename, content)

    zip_buffer.seek(0)
    filename = f"hrv_recordings_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip"
    return StreamingResponse(
        iter([zip_buffer.getvalue()]),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

@router.delete("/recordings/{recording_id}")
async def delete_hrv_recording(
    recording_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    platform_check: User = Depends(require_mobile_platform),
):
    try:
        recording_uuid = uuid.UUID(recording_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid recording_id")

    recording = db.query(HrvBulkRecording).filter(
        HrvBulkRecording.id == recording_uuid,
        HrvBulkRecording.operator_id == current_user.id,
    ).first()

    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    db.query(HrvBulkReading).filter(
        HrvBulkReading.recording_id == recording.id
    ).delete(synchronize_session=False)
    db.delete(recording)
    db.commit()

    return {"success": True, "deleted_id": str(recording.id)}

@router.delete("/recordings")
async def delete_all_hrv_recordings(
    confirm: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    platform_check: User = Depends(require_mobile_platform),
):
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="confirm=true is required to delete all recordings",
        )

    recordings = db.query(HrvBulkRecording.id).filter(
        HrvBulkRecording.operator_id == current_user.id
    ).all()
    recording_ids = [recording_id for (recording_id,) in recordings]

    if not recording_ids:
        return {"success": True, "deleted_count": 0}

    db.query(HrvBulkReading).filter(
        HrvBulkReading.recording_id.in_(recording_ids)
    ).delete(synchronize_session=False)

    deleted_count = db.query(HrvBulkRecording).filter(
        HrvBulkRecording.id.in_(recording_ids)
    ).delete(synchronize_session=False)

    db.commit()

    return {"success": True, "deleted_count": deleted_count}
