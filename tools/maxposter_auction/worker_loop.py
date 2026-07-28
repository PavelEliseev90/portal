"""
Фоновый цикл площадки без открытого viewer.html.

Каждые WORKER_INTERVAL_SEC секунд:
  1) reload лотов (script_auction)
  2) расчёт + автоставка через API портала + /api/bid (если WORKER_AUTO_BID=1)
  3) опрос итогов (если WORKER_OUTCOMES=1)

Запуск: из server.main() при WORKER_INTERVAL_SEC>0 (по умолчанию 180, если задан FIXED dealer).
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any

logger = logging.getLogger("maxposter.worker")


def _env_bool(name: str, default: bool = False) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _http_json(url: str, payload: dict | None = None, timeout: float = 120) -> dict:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if payload is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw) if raw else {}


def _auth() -> tuple[str, str]:
    return (
        (os.environ.get("MAXPOSTER_EMAIL") or "").strip(),
        (os.environ.get("MAXPOSTER_PASSWORD") or ""),
    )


def _portal_base() -> str:
    return (os.environ.get("PORTAL_BASE") or os.environ.get("PORTAL_BASE_URL") or "https://ah.kors-group.com").rstrip("/")


def _local_base() -> str:
    host = os.environ.get("HOST", "127.0.0.1")
    port = os.environ.get("PORT", "8005")
    return f"http://{host}:{port}"


def _dealer_id() -> str:
    return (os.environ.get("MAXPOSTER_DEALER_ID") or "").strip()


def _load_offers(out_json: str) -> list[dict]:
    if not os.path.exists(out_json):
        return []
    try:
        with open(out_json, encoding="utf-8") as f:
            data = json.load(f)
        offers = data.get("offers") or []
        return offers if isinstance(offers, list) else []
    except Exception:
        return []


def _offer_ids(offer: dict) -> tuple[Any, Any, dict]:
    lot = offer.get("lot") if isinstance(offer.get("lot"), dict) else {}
    lot_offer_id = offer.get("lotOfferId") or lot.get("lotOfferId")
    lot_id = lot.get("lotId") or offer.get("lotId")
    return lot_offer_id, lot_id, lot


def _build_calc_payload(offer: dict, dealer_id: str) -> dict:
    lot_offer_id, lot_id, lot_src = _offer_ids(offer)
    lot = dict(lot_src)
    if dealer_id:
        try:
            lot["dealerId"] = int(dealer_id)
        except ValueError:
            lot["dealerId"] = dealer_id
    if lot_id is not None and lot_id != "":
        lot["lotId"] = int(lot_id)
    if lot_offer_id is not None and lot_offer_id != "":
        lot["lotOfferId"] = int(lot_offer_id)
    if not lot.get("finishAt") and lot.get("originFinishAt"):
        lot["finishAt"] = lot["originFinishAt"]
    payload = {
        **offer,
        "lot": lot,
        "lotId": int(lot_id) if lot_id not in (None, "") else None,
        "lotOfferId": int(lot_offer_id) if lot_offer_id not in (None, "") else None,
        "dealerId": int(dealer_id) if str(dealer_id).isdigit() else dealer_id,
        "minPrice": lot.get("minPrice"),
        "minAvailableBid": lot.get("minAvailableBid"),
        "maxAvailableBid": lot.get("maxAvailableBid"),
        "maxBid": lot.get("maxBid"),
        "vehicle": lot.get("vehicle"),
        "autohubVehicle": lot.get("autohubVehicle"),
        "autoteka": lot.get("autoteka"),
        "description": lot.get("description"),
        "sellerPlaceName": lot.get("sellerPlaceName"),
        "finishAt": lot.get("finishAt") or lot.get("originFinishAt"),
        "expiresAt": lot.get("expiresAt"),
        "originFinishAt": lot.get("originFinishAt"),
        "images": lot.get("images") or offer.get("images"),
        "badges": offer.get("badges") or lot.get("badges"),
        "forceRecalc": True,
    }
    return payload


def _parse_calc_answer(data: dict) -> dict:
    if not isinstance(data, dict):
        return {"ok": False, "estimation_price": None}
    answer = data.get("answer") if isinstance(data.get("answer"), dict) else data
    price = answer.get("estimation_price") or answer.get("buyoutPrice") or data.get("estimation_price")
    return {"ok": True, "estimation_price": price, "raw": data, "answer": answer}


def run_reload(email: str, password: str, dealer_id: str) -> dict:
    return _http_json(
        f"{_local_base()}/api/reload",
        {"email": email, "password": password, "dealerId": dealer_id},
        timeout=12 * 60,
    )


def run_calc_and_autobid(email: str, password: str, dealer_id: str, out_json: str) -> dict:
    portal = _portal_base()
    offers = _load_offers(out_json)
    stats = {"offers": len(offers), "calc_ok": 0, "calc_fail": 0, "bid_ok": 0, "bid_skip": 0, "bid_fail": 0}
    for offer in offers:
        lot_offer_id, lot_id, lot = _offer_ids(offer)
        if not lot_offer_id or not lot_id:
            continue
        try:
            calc_data = _http_json(
                f"{portal}/api/calculate_car/",
                _build_calc_payload(offer, dealer_id),
                timeout=180,
            )
            parsed = _parse_calc_answer(calc_data)
            if not parsed.get("estimation_price"):
                stats["calc_fail"] += 1
                continue
            stats["calc_ok"] += 1
            buyout = parsed["estimation_price"]
            veh = lot.get("vehicle") or {}
            year = None
            if isinstance(veh.get("year"), dict):
                year = veh["year"].get("name") or veh["year"].get("id")
            else:
                year = veh.get("year")
            mileage = veh.get("mileage")
            if mileage is None:
                ah = lot.get("autohubVehicle") or {}
                mileage = ah.get("kmDistance")

            decide = _http_json(
                f"{portal}/api/avito_auction_auto_bid_decide/",
                {
                    "lotId": int(lot_id),
                    "lotOfferId": int(lot_offer_id),
                    "buyoutPrice": buyout,
                    "minAvailableBid": lot.get("minAvailableBid"),
                    "maxBid": lot.get("maxBid") if lot.get("maxBid") not in (0, "0") else None,
                    "minBidStep": offer.get("minBidStep"),
                    "ourBid": offer.get("bid") or 0,
                    "minPrice": lot.get("minPrice"),
                    "year": year,
                    "mileage": mileage,
                    "autoteka": lot.get("autoteka"),
                },
                timeout=60,
            )
            if not decide.get("should_bid"):
                stats["bid_skip"] += 1
                continue
            amount = decide.get("bid_amount")
            if not amount:
                stats["bid_skip"] += 1
                continue

            bid_payload = {
                "lotId": int(lot_id),
                "avgPriceWithCorrection": None,
                "saleCost": lot.get("saleCost") or lot.get("minPrice") or 0,
                "presalePreparationCost": lot.get("presalePreparationCost") or 0,
                "isBuyoutOnSiteAvailable": bool(lot.get("isBuyoutOnSiteAvailable")),
                "isInspectionOnSiteAvailable": bool(lot.get("isInspectionOnSiteAvailable")),
                "isPriceGuaranteed": bool(lot.get("isPriceGuaranteed")),
                "bid": int(amount),
            }
            bid_resp = _http_json(
                f"{_local_base()}/api/bid",
                {
                    "email": email,
                    "password": password,
                    "dealerId": dealer_id,
                    "lotOfferId": int(lot_offer_id),
                    "lotId": int(lot_id),
                    "dryRun": False,
                    "bidAmount": int(amount),
                    "bidPayload": bid_payload,
                },
                timeout=180,
            )
            if bid_resp.get("ok"):
                stats["bid_ok"] += 1
                # регистрация на портале
                try:
                    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                    _http_json(
                        f"{portal}/api/avito_auction_bid_set/",
                        {
                            "LotOfferId": int(lot_offer_id),
                            "LotId": int(lot_id),
                            "bid": int(amount),
                            "bidMadeAt": now,
                            "dealerId": int(dealer_id) if str(dealer_id).isdigit() else dealer_id,
                        },
                        timeout=60,
                    )
                except Exception as exc:
                    logger.warning("portal bid_set failed lot=%s: %s", lot_id, exc)
            else:
                stats["bid_fail"] += 1
                logger.warning("bid fail lot=%s: %s", lot_id, bid_resp.get("error") or bid_resp)
        except Exception as exc:
            stats["calc_fail"] += 1
            logger.warning("calc/bid cycle fail lotOfferId=%s: %s", lot_offer_id, exc)
        time.sleep(0.4)
    return stats


def run_outcomes(email: str, password: str, dealer_id: str) -> dict:
    portal = _portal_base()
    url = (
        f"{portal}/api/avito_auction_outcome_queue/"
        f"?limit=30&lookback_days=30&dealer_id={urllib.parse.quote(str(dealer_id))}"
    )
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        q = json.loads(resp.read().decode("utf-8", errors="replace") or "{}")

    if q.get("enabled") is False:
        return {"ok": True, "skipped": True, "reason": "disabled"}
    items = [it for it in (q.get("items") or []) if isinstance(it, dict)]
    items = [it for it in items if not it.get("dealerId") or str(it.get("dealerId")) == str(dealer_id)]
    ok_n = fail_n = 0
    for item in items:
        try:
            row = _http_json(
                f"{_local_base()}/api/outcomes",
                {
                    "email": email,
                    "password": password,
                    "dealerId": dealer_id,
                    "portalBase": portal,
                    "items": [item],
                },
                timeout=180,
            )
            if row.get("ok"):
                ok_n += 1
            else:
                fail_n += 1
        except Exception as exc:
            fail_n += 1
            logger.warning("outcome fail: %s", exc)
        time.sleep(0.7)
    return {"ok": fail_n == 0, "okCount": ok_n, "failCount": fail_n, "total": len(items)}


def run_one_cycle(out_json: str) -> dict:
    email, password = _auth()
    dealer_id = _dealer_id()
    if not email or not password:
        return {"ok": False, "error": "no_auth_env"}
    if not dealer_id:
        return {"ok": False, "error": "no_dealer"}

    summary: dict[str, Any] = {"dealerId": dealer_id, "ts": datetime.utcnow().isoformat()}
    try:
        reload_res = run_reload(email, password, dealer_id)
        summary["reload"] = {
            "ok": bool(reload_res.get("ok")),
            "count": reload_res.get("count"),
            "error": reload_res.get("error"),
        }
    except Exception as exc:
        summary["reload"] = {"ok": False, "error": str(exc)[:300]}
        return summary

    if _env_bool("WORKER_AUTO_BID", True):
        try:
            summary["autobid"] = run_calc_and_autobid(email, password, dealer_id, out_json)
        except Exception as exc:
            summary["autobid"] = {"ok": False, "error": str(exc)[:300]}

    if _env_bool("WORKER_OUTCOMES", True):
        try:
            summary["outcomes"] = run_outcomes(email, password, dealer_id)
        except Exception as exc:
            summary["outcomes"] = {"ok": False, "error": str(exc)[:300]}

    summary["ok"] = bool((summary.get("reload") or {}).get("ok"))
    return summary


class InstanceWorker:
    def __init__(self, out_json: str):
        self.out_json = out_json
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.last_summary: dict | None = None
        self.last_error: str | None = None
        self.running = False

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="instance-worker", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def status(self) -> dict:
        interval = _env_int("WORKER_INTERVAL_SEC", 0)
        return {
            "enabled": interval > 0,
            "intervalSec": interval,
            "running": self.running,
            "autoBid": _env_bool("WORKER_AUTO_BID", True),
            "outcomes": _env_bool("WORKER_OUTCOMES", True),
            "lastSummary": self.last_summary,
            "lastError": self.last_error,
        }

    def _loop(self):
        interval = _env_int("WORKER_INTERVAL_SEC", 180)
        if interval <= 0:
            return
        # небольшая пауза после старта HTTP
        self._stop.wait(5)
        while not self._stop.is_set():
            self.running = True
            try:
                summary = run_one_cycle(self.out_json)
                self.last_summary = summary
                self.last_error = summary.get("error") or (summary.get("reload") or {}).get("error")
                logger.info(
                    "worker cycle dealer=%s reload_ok=%s autobid=%s outcomes=%s",
                    summary.get("dealerId"),
                    (summary.get("reload") or {}).get("ok"),
                    summary.get("autobid"),
                    summary.get("outcomes"),
                )
                print(
                    f"[worker] dealer={summary.get('dealerId')} "
                    f"reload={ (summary.get('reload') or {}).get('ok') } "
                    f"lots={(summary.get('reload') or {}).get('count')} "
                    f"autobid={summary.get('autobid')} "
                    f"outcomes={summary.get('outcomes')}",
                    flush=True,
                )
            except Exception as exc:
                self.last_error = str(exc)[:400]
                logger.exception("worker cycle failed")
                print(f"[worker] ERROR: {exc}", flush=True)
            finally:
                self.running = False
            self._stop.wait(max(30, interval))


def start_worker_if_configured(out_json: str) -> InstanceWorker | None:
    """
    Включает фоновый цикл, если WORKER_INTERVAL_SEC>0.
    Для multi-instance (есть MAXPOSTER_DEALER_ID) по умолчанию 180 сек.
    Отключить: WORKER_INTERVAL_SEC=0
    """
    raw = (os.environ.get("WORKER_INTERVAL_SEC") or "").strip()
    if raw == "":
        if (os.environ.get("MAXPOSTER_DEALER_ID") or "").strip():
            os.environ["WORKER_INTERVAL_SEC"] = "180"
        else:
            return None
    if _env_int("WORKER_INTERVAL_SEC", 0) <= 0:
        return None
    worker = InstanceWorker(out_json)
    worker.start()
    print(
        f"[worker] фон включён: каждые {_env_int('WORKER_INTERVAL_SEC', 180)} с "
        f"(reload + автоставки={_env_bool('WORKER_AUTO_BID', True)} + итоги={_env_bool('WORKER_OUTCOMES', True)})",
        flush=True,
    )
    return worker
