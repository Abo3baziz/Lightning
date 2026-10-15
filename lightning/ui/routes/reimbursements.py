from __future__ import annotations

from fastapi import APIRouter, Request

from lightning.core.errors import LightningError

from ..web import container, redirect, render

router = APIRouter(prefix="/reimbursements")


def _context(request: Request, error: str = "", values: dict | None = None):
    c = container(request)
    return {"claims": c.reimbursements.list_claims(),
            "expenses": c.reimbursements.eligible_expenses(),
            "receipts": c.reimbursements.available_receipts(),
            "counterparties": c.counterparties.list_active(),
            "base": c.base_currency, "error": error,
            "values": values or {"transaction_id": str(request.query_params.get("expense_id", "")), "expected": "", "payer_id": "", "due_date": ""}}


@router.get("")
async def reimbursements_page(request: Request):
    return render(request, "reimbursements.html", **_context(request))


@router.post("")
async def create_claim(request: Request):
    c = container(request)
    form = await request.form()
    values = {key: str(form.get(key, "")).strip()
              for key in ("transaction_id", "expected", "payer_id", "due_date")}
    try:
        if not values["transaction_id"].isdigit():
            raise ValueError
        transaction_id = int(values["transaction_id"])
        if values["payer_id"] and not values["payer_id"].isdigit():
            raise ValueError
        payer_id = int(values["payer_id"]) if values["payer_id"] else None
        claim = c.reimbursements.create_claim(transaction_id, values["expected"], payer_id,
                                              values["due_date"] or None)
    except (ValueError, LightningError) as exc:
        message = exc.message if isinstance(exc, LightningError) else "Choose an expense and enter an amount."
        return render(request, "reimbursements.html", status_code=400, **_context(request, message, values))
    return redirect("/reimbursements", f"Created reimbursement claim for {claim['expense']['ref']}.")


@router.post("/{claim_id:int}/receipts")
async def link_receipt(request: Request, claim_id: int):
    c = container(request)
    form = await request.form()
    receipt_id = str(form.get("receipt_id", "")).strip()
    amount = str(form.get("amount", "")).strip()
    try:
        if not receipt_id.isdigit():
            raise ValueError
        c.reimbursements.link_receipt(claim_id, int(receipt_id), amount)
    except (ValueError, LightningError) as exc:
        message = exc.message if isinstance(exc, LightningError) else "Choose a receipt and enter an amount."
        return render(request, "reimbursements.html", status_code=400, **_context(request, message))
    return redirect("/reimbursements", "Linked the receipt; no income or cash entry was added.")


@router.post("/{claim_id:int}/receipts/{link_id:int}/unlink")
async def unlink_receipt(request: Request, claim_id: int, link_id: int):
    try:
        container(request).reimbursements.unlink_receipt(claim_id, link_id)
    except LightningError as exc:
        return redirect("/reimbursements", exc.message)
    return redirect("/reimbursements", "Removed the receipt link.")


@router.post("/{claim_id:int}/delete")
async def delete_claim(request: Request, claim_id: int):
    try:
        container(request).reimbursements.delete_claim(claim_id)
    except LightningError as exc:
        return redirect("/reimbursements", exc.message)
    return redirect("/reimbursements", "Deleted the reimbursement claim and its links.")
