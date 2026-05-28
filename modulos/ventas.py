"""
Sales module: catalog, quotes, and acceptance with auto payment link.
"""

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Optional
from uuid import uuid4

if TYPE_CHECKING:
    from modulos.links_pago import LinksPagoModule

logger = logging.getLogger(__name__)


class SalesModule:
    """Sales operations for the agent."""

    def __init__(
        self,
        supabase_client: Any,
        links_pago_module: Optional["LinksPagoModule"] = None,
    ):
        self.supabase = supabase_client
        self.links_pago = links_pago_module

    async def get_catalog(self, client_id: str) -> list[dict[str, Any]]:
        """Return active products for a client."""
        try:
            response = (
                self.supabase.table("product_catalog")
                .select("*")
                .eq("cliente_id", client_id)
                .eq("activo", True)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error fetching catalog: {e}")
            return []

    async def create_quote(
        self,
        client_id: str,
        user_id: str,
        productos: list[str],
        cantidades: list[int],
        descuento_porcentaje: float = 0,
        notas: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create a quote from product names/IDs and persist it."""
        try:
            if len(productos) != len(cantidades):
                raise ValueError("productos and cantidades must have the same length")

            catalog = await self.get_catalog(client_id)
            # Match by id or by nombre (case-insensitive) so GPT can pass names
            catalog_by_id = {p["id"]: p for p in catalog}
            catalog_by_name = {p["nombre"].lower(): p for p in catalog}

            items: list[dict[str, Any]] = []
            subtotal = 0.0

            for prod_ref, cantidad in zip(productos, cantidades):
                product = catalog_by_id.get(prod_ref) or catalog_by_name.get(
                    prod_ref.lower()
                )
                if not product:
                    logger.warning(f"Product '{prod_ref}' not found in catalog for client {client_id}")
                    continue

                item_total = float(product.get("precio", 0)) * cantidad
                items.append(
                    {
                        "product_id": product["id"],
                        "product_name": product.get("nombre", ""),
                        "quantity": cantidad,
                        "unit_price": float(product.get("precio", 0)),
                        "total": item_total,
                    }
                )
                subtotal += item_total

            discount_amount = subtotal * (descuento_porcentaje / 100)
            total = subtotal - discount_amount

            quote = {
                "id": str(uuid4()),
                "cliente_id": client_id,
                "user_id": user_id,
                "items": items,
                "subtotal": round(subtotal, 2),
                "discount_percentage": descuento_porcentaje,
                "discount_amount": round(discount_amount, 2),
                "total": round(total, 2),
                "moneda": "USD",
                "notas": notas,
                "status": "pending",
                "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat(),
                "created_at": datetime.utcnow().isoformat(),
            }

            self.supabase.table("quotes").insert(quote).execute()
            logger.info(f"Quote created: {quote['id']} for user {user_id}")
            return quote

        except Exception as e:
            logger.error(f"Error creating quote: {e}")
            return {"error": str(e)}

    async def apply_discount(
        self,
        quote_id: str,
        descuento_porcentaje: float,
        razon: str = "",
    ) -> dict[str, Any]:
        """Apply or change the discount on an existing quote."""
        try:
            response = (
                self.supabase.table("quotes").select("*").eq("id", quote_id).single().execute()
            )
            quote = response.data
            subtotal = quote["subtotal"]
            discount_amount = subtotal * (descuento_porcentaje / 100)
            new_total = subtotal - discount_amount

            updated = {
                "discount_percentage": descuento_porcentaje,
                "discount_amount": round(discount_amount, 2),
                "total": round(new_total, 2),
                "discount_reason": razon,
                "updated_at": datetime.utcnow().isoformat(),
            }
            self.supabase.table("quotes").update(updated).eq("id", quote_id).execute()
            logger.info(f"Discount applied to quote {quote_id}: {descuento_porcentaje}%")
            return {**quote, **updated}

        except Exception as e:
            logger.error(f"Error applying discount: {e}")
            return {"error": str(e)}

    async def accept_quote(
        self,
        quote_id: str,
        client_id: str,
        user_id: str,
        proveedor: str = "stripe",
    ) -> dict[str, Any]:
        """
        Mark a quote as accepted and auto-generate a payment link.

        Returns the quote total and the ready-to-send payment URL.
        """
        try:
            response = (
                self.supabase.table("quotes").select("*").eq("id", quote_id).single().execute()
            )
            quote = response.data

            if quote.get("status") not in ("pending", "sent"):
                return {"error": f"La cotización ya está en estado '{quote.get('status')}'"}

            payment_result: dict[str, Any] = {}
            payment_link_id: Optional[str] = None

            if self.links_pago and quote.get("total", 0) > 0:
                items_desc = ", ".join(
                    f"{it['product_name']} x{it['quantity']}"
                    for it in (quote.get("items") or [])
                )
                descripcion = items_desc or "Cotización aceptada"

                payment_result = await self.links_pago.generar_link_pago(
                    client_id=client_id,
                    usuario_id=user_id,
                    monto=quote["total"],
                    descripcion=descripcion,
                    proveedores=[proveedor],
                )
                opciones = payment_result.get("payment_options", {}).get("opciones", {})
                first_option = next(iter(opciones.values()), {})
                payment_link_id = first_option.get("link_id")

            self.supabase.table("quotes").update(
                {
                    "status": "accepted",
                    "accepted_at": datetime.utcnow().isoformat(),
                    "payment_link_id": payment_link_id,
                    "updated_at": datetime.utcnow().isoformat(),
                }
            ).eq("id", quote_id).execute()

            # Decrement stock for each item (only when stock is tracked, i.e. not NULL)
            for item in quote.get("items") or []:
                prod_id = item.get("product_id")
                qty = item.get("quantity", 1)
                if prod_id:
                    try:
                        prod_resp = (
                            self.supabase.table("product_catalog")
                            .select("stock")
                            .eq("id", prod_id)
                            .single()
                            .execute()
                        )
                        current_stock = prod_resp.data.get("stock")
                        if current_stock is not None:
                            new_stock = max(0, current_stock - qty)
                            self.supabase.table("product_catalog").update(
                                {"stock": new_stock, "updated_at": datetime.utcnow().isoformat()}
                            ).eq("id", prod_id).execute()
                    except Exception as stock_err:
                        logger.warning(f"Could not decrement stock for product {prod_id}: {stock_err}")

            logger.info(f"Quote {quote_id} accepted by user {user_id}")

            result: dict[str, Any] = {
                "success": True,
                "quote_id": quote_id,
                "total": quote["total"],
                "moneda": quote.get("moneda", "USD"),
            }
            if payment_result.get("success"):
                opciones = payment_result["payment_options"]["opciones"]
                first = next(iter(opciones.values()), {})
                result["payment_url"] = first.get("payment_url")
                result["proveedor"] = proveedor
            return result

        except Exception as e:
            logger.error(f"Error accepting quote: {e}")
            return {"error": str(e)}

    async def reject_quote(self, quote_id: str, razon: str = "") -> dict[str, Any]:
        """Mark a quote as rejected."""
        try:
            self.supabase.table("quotes").update(
                {
                    "status": "rejected",
                    "rejected_at": datetime.utcnow().isoformat(),
                    "discount_reason": razon,
                    "updated_at": datetime.utcnow().isoformat(),
                }
            ).eq("id", quote_id).execute()
            logger.info(f"Quote {quote_id} rejected. Reason: {razon}")
            return {"success": True, "quote_id": quote_id}
        except Exception as e:
            logger.error(f"Error rejecting quote: {e}")
            return {"error": str(e)}

    async def get_sales_pipeline(self, client_id: str) -> dict[str, Any]:
        """Return pipeline summary grouped by status."""
        try:
            response = (
                self.supabase.table("quotes")
                .select("status, total")
                .eq("cliente_id", client_id)
                .execute()
            )
            pipeline: dict[str, dict[str, Any]] = {
                s: {"count": 0, "total_value": 0}
                for s in ("pending", "sent", "accepted", "rejected", "expired")
            }
            for quote in response.data or []:
                status = quote.get("status", "pending")
                if status in pipeline:
                    pipeline[status]["count"] += 1
                    pipeline[status]["total_value"] += quote.get("total", 0)
            return pipeline
        except Exception as e:
            logger.error(f"Error fetching sales pipeline: {e}")
            return {}
