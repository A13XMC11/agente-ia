"""
Catalog sync module: import products from CSV, Excel, or Google Sheets.

Single source of truth is always product_catalog in Supabase.
This module handles the multiple ingestion paths that populate it.

Upsert key priority:
  1. sku  (if both the file and the existing row have it)
  2. nombre (case-insensitive fallback)
"""

import io
import logging
import re
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

import httpx
import pandas as pd

logger = logging.getLogger(__name__)

# Columns accepted from external files (all optional except nombre/precio)
_COLUMN_ALIASES: dict[str, str] = {
    # español
    "nombre": "nombre",
    "name": "nombre",
    "producto": "nombre",
    "descripcion": "descripcion",
    "description": "descripcion",
    "precio": "precio",
    "price": "precio",
    "costo": "precio",
    "stock": "stock",
    "cantidad": "stock",
    "inventory": "stock",
    "moneda": "moneda",
    "currency": "moneda",
    "categoria": "categoria",
    "category": "categoria",
    "imagen": "imagen_url",
    "imagen_url": "imagen_url",
    "image_url": "imagen_url",
    "sku": "sku",
    "codigo": "sku",
    "code": "sku",
    "ref": "sku",
}


class CatalogSyncModule:
    """Import and sync product catalogs from multiple sources."""

    def __init__(self, supabase_client: Any):
        self.supabase = supabase_client

    # ── Private helpers ───────────────────────────────────────────────────────

    def _normalize_df(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        """Rename columns to internal names and drop rows without nombre/precio."""
        df.columns = [c.strip().lower() for c in df.columns]
        df = df.rename(columns=_COLUMN_ALIASES)

        if "nombre" not in df.columns:
            raise ValueError("El archivo no tiene columna 'nombre' o equivalente.")
        if "precio" not in df.columns:
            raise ValueError("El archivo no tiene columna 'precio' o equivalente.")

        df = df[df["nombre"].notna() & (df["nombre"].astype(str).str.strip() != "")]
        df["precio"] = pd.to_numeric(df["precio"], errors="coerce").fillna(0)

        records = []
        for _, row in df.iterrows():
            product: dict[str, Any] = {
                "nombre": str(row["nombre"]).strip(),
                "precio": float(row["precio"]),
            }
            for field in ("descripcion", "moneda", "categoria", "imagen_url", "sku"):
                if field in row and pd.notna(row[field]):
                    product[field] = str(row[field]).strip() or None
            if "stock" in row and pd.notna(row["stock"]):
                try:
                    product["stock"] = int(row["stock"])
                except (ValueError, TypeError):
                    pass
            records.append(product)

        return records

    def _upsert_products(
        self, client_id: str, products: list[dict[str, Any]]
    ) -> dict[str, int]:
        """Upsert products into product_catalog. Returns {created, updated, skipped}."""
        existing_resp = (
            self.supabase.table("product_catalog")
            .select("id, sku, nombre")
            .eq("cliente_id", client_id)
            .execute()
        )
        existing = existing_resp.data or []
        by_sku: dict[str, str] = {
            r["sku"].lower(): r["id"] for r in existing if r.get("sku")
        }
        by_nombre: dict[str, str] = {
            r["nombre"].lower(): r["id"] for r in existing
        }

        created = updated = skipped = 0
        now = datetime.utcnow().isoformat()

        for product in products:
            existing_id: Optional[str] = None
            sku = (product.get("sku") or "").lower()
            nombre = product["nombre"].lower()

            if sku and sku in by_sku:
                existing_id = by_sku[sku]
            elif nombre in by_nombre:
                existing_id = by_nombre[nombre]

            if existing_id:
                self.supabase.table("product_catalog").update(
                    {**product, "updated_at": now}
                ).eq("id", existing_id).execute()
                updated += 1
            else:
                new_row = {
                    "id": str(uuid4()),
                    "cliente_id": client_id,
                    **product,
                    "activo": True,
                    "created_at": now,
                    "updated_at": now,
                }
                self.supabase.table("product_catalog").insert(new_row).execute()
                created += 1
                if sku:
                    by_sku[sku] = new_row["id"]
                by_nombre[nombre] = new_row["id"]

        return {"created": created, "updated": updated, "skipped": skipped}

    @staticmethod
    def _sheets_to_csv_url(url: str) -> str:
        """
        Convert any Google Sheets URL variant to a public CSV URL.

        Uses /pub?output=csv instead of /export?format=csv because the export
        endpoint redirects to a signed googleusercontent.com URL that requires
        Google session cookies — causing 400 errors in server-side HTTP clients.

        The sheet MUST be published to the web:
          File → Share → Publish to web → select the sheet → CSV → Publish

        Handles two URL variants:
          1. Published format: /d/e/{2PACX-...}/pub  (from "Publish to web" dialog)
          2. Regular edit URL: /d/{SPREADSHEET_ID}/edit  (converted to /pub — requires sheet to be published)

        The published key always starts with "2PACX-". If the URL contains /d/e/
        but no valid key, the sheet was not properly published.
        """
        gid_match = re.search(r"gid=(\d+)", url)
        gid = gid_match.group(1) if gid_match else "0"

        # Case 1: Published format /d/e/{PUBLISHED_KEY}/
        # Published keys start with "2PACX-" and are long alphanumeric strings.
        pub_match = re.search(r"/spreadsheets/d/e/([a-zA-Z0-9_-]{20,})", url)
        if pub_match:
            published_id = pub_match.group(1)
            return (
                f"https://docs.google.com/spreadsheets/d/e/{published_id}"
                f"/pub?output=csv&gid={gid}"
            )

        # Case 2: Regular spreadsheet edit URL /d/{SPREADSHEET_ID}/
        # This only works if the sheet has been published to the web.
        sheet_match = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]{20,})", url)
        if sheet_match:
            sheet_id = sheet_match.group(1)
            return (
                f"https://docs.google.com/spreadsheets/d/{sheet_id}"
                f"/pub?output=csv&gid={gid}"
            )

        raise ValueError(
            "URL de Google Sheets no válida. "
            "Asegúrate de publicar la hoja: Archivo → Compartir → Publicar en la web → "
            "selecciona la pestaña → formato CSV → Publicar. "
            "La URL publicada tendrá el formato: "
            "https://docs.google.com/spreadsheets/d/e/2PACX-.../pub?output=csv"
        )

    # ── Public API ────────────────────────────────────────────────────────────

    async def import_from_csv(
        self, client_id: str, csv_text: str
    ) -> dict[str, Any]:
        """Parse CSV text and upsert into product_catalog."""
        try:
            df = pd.read_csv(io.StringIO(csv_text))
            products = self._normalize_df(df)
            summary = self._upsert_products(client_id, products)
            logger.info(f"CSV import for {client_id}: {summary}")
            return {"success": True, "total_rows": len(products), **summary}
        except Exception as e:
            logger.error(f"CSV import error for {client_id}: {e}")
            return {"success": False, "error": str(e)}

    async def import_from_excel(
        self, client_id: str, excel_bytes: bytes
    ) -> dict[str, Any]:
        """Parse Excel (.xlsx/.xls) bytes and upsert into product_catalog."""
        try:
            df = pd.read_excel(io.BytesIO(excel_bytes), engine="openpyxl")
            products = self._normalize_df(df)
            summary = self._upsert_products(client_id, products)
            logger.info(f"Excel import for {client_id}: {summary}")
            return {"success": True, "total_rows": len(products), **summary}
        except Exception as e:
            logger.error(f"Excel import error for {client_id}: {e}")
            return {"success": False, "error": str(e)}

    async def sync_from_sheets(
        self, client_id: str, sheets_url: str
    ) -> dict[str, Any]:
        """Fetch a public Google Sheets as CSV and upsert into product_catalog."""
        try:
            csv_url = self._sheets_to_csv_url(sheets_url)
            async with httpx.AsyncClient(follow_redirects=True, timeout=15) as http:
                response = await http.get(csv_url)
                response.raise_for_status()

            result = await self.import_from_csv(client_id, response.text)

            # Update ultimo_sync timestamp
            self.supabase.table("catalog_sync_config").update(
                {"ultimo_sync": datetime.utcnow().isoformat()}
            ).eq("cliente_id", client_id).execute()

            return result
        except Exception as e:
            logger.error(f"Sheets sync error for {client_id}: {e}")
            return {"success": False, "error": str(e)}

    async def sync_from_webhook(
        self, client_id: str, webhook_url: str
    ) -> dict[str, Any]:
        """
        Fetch product list from client's own API.
        Expects JSON: list of objects or {"products": [...]} / {"data": [...]}.
        """
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=15) as http:
                response = await http.get(webhook_url)
                response.raise_for_status()

            payload = response.json()
            if isinstance(payload, list):
                rows = payload
            elif isinstance(payload, dict):
                rows = payload.get("products") or payload.get("data") or payload.get("items") or []
            else:
                raise ValueError("Respuesta del webhook no reconocida")

            df = pd.DataFrame(rows)
            products = self._normalize_df(df)
            summary = self._upsert_products(client_id, products)

            self.supabase.table("catalog_sync_config").update(
                {"ultimo_sync": datetime.utcnow().isoformat()}
            ).eq("cliente_id", client_id).execute()

            logger.info(f"Webhook sync for {client_id}: {summary}")
            return {"success": True, "total_rows": len(products), **summary}
        except Exception as e:
            logger.error(f"Webhook sync error for {client_id}: {e}")
            return {"success": False, "error": str(e)}

    async def sync_all_auto_clients(self) -> dict[str, Any]:
        """
        Called by APScheduler. Syncs every active client with tipo='sheets' or 'webhook'.
        Respects sync_interval_minutes so we don't hammer sources too frequently.
        """
        try:
            response = (
                self.supabase.table("catalog_sync_config")
                .select("*")
                .eq("activo", True)
                .in_("tipo", ["sheets", "webhook"])
                .execute()
            )
            configs = response.data or []
        except Exception as e:
            logger.error(f"Error fetching sync configs: {e}")
            return {"synced": 0, "errors": 0}

        synced = errors = 0
        now = datetime.utcnow()

        for cfg in configs:
            client_id = cfg["cliente_id"]
            ultimo = cfg.get("ultimo_sync")
            interval = cfg.get("sync_interval_minutes", 60)

            # Skip if synced recently
            if ultimo:
                from datetime import timezone
                last = datetime.fromisoformat(ultimo.replace("Z", "+00:00"))
                elapsed_minutes = (now.replace(tzinfo=timezone.utc) - last).seconds / 60
                if elapsed_minutes < interval:
                    continue

            try:
                if cfg["tipo"] == "sheets" and cfg.get("sheets_url"):
                    result = await self.sync_from_sheets(client_id, cfg["sheets_url"])
                elif cfg["tipo"] == "webhook" and cfg.get("webhook_url"):
                    result = await self.sync_from_webhook(client_id, cfg["webhook_url"])
                else:
                    continue

                if result.get("success"):
                    synced += 1
                else:
                    errors += 1
            except Exception as e:
                logger.error(f"Auto-sync failed for client {client_id}: {e}")
                errors += 1

        logger.info(f"Auto catalog sync complete: {synced} synced, {errors} errors")
        return {"synced": synced, "errors": errors}
