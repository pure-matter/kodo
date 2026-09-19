import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..db import get_db
from ..ingestion import import_statement
from ..models import Account
from ..schemas import ImportSummaryOut

router = APIRouter(prefix="/accounts", tags=["imports"])


@router.post("/{account_id}/import", response_model=ImportSummaryOut)
def import_account_statement(
    account_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)
):
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(404, "Account not found")

    suffix = Path(file.filename or "").suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        summary = import_statement(db, account, tmp_path)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return summary
