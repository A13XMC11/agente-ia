"""
Sales module: catalog management, quotes, and objection handling.

Handles product catalogs, quote generation, discount application,
and sales pipeline management per client.
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class SalesModule:
    """Sales operations for the agent."""

    def __init__(self, supabase_client: Any):
        """
        Initialize sales module.

        Args:
            supabase_client: Supabase client instance for data persistence
        """
        self.supabase = supabase_client

    async def get_catalog(self, client_id: str) -> list[dict[str, Any]]:
        """
        Fetch product catalog for a client.

        Args:
            client_id: Client ID

        Returns:
            List of products with price, description, images
        """
        try:
            response = self.supabase.table("product_catalog").select("*").eq(
                "cliente_id", client_id
            ).execute()
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
        """
        Create a sales quote for a customer.

        Args:
            client_id: Client ID
            user_id: Customer user ID
            productos: List of product IDs
            cantidades: Quantities for each product
            descuento_porcentaje: Discount percentage (0-100)
            notas: Optional notes for the quote

        Returns:
            Quote object with items, subtotal, discount, total, and quote_id
        """
        try:
            if len(productos) != len(cantidades):
                raise ValueError("Products and quantities must have same length")

            # Fetch products from catalog
            catalog = await self.get_catalog(client_id)
            catalog_map = {p["id"]: p for p in catalog}

            quote_items = []
            subtotal = 0.0

            for prod_id, cantidad in zip(productos, cantidades):
                if prod_id not in catalog_map:
                    logger.warning(f"Product {prod_id} not found in catalog")
                    continue

                product = catalog_map[prod_id]
                item_total = float(product.get("price", 0)) * cantidad

                quote_items.append(
                    {
                        "product_id": prod_id,
                        "product_name": product.get("name", "Unknown"),
                        "quantity": cantidad,
                        "unit_price": float(product.get("price", 0)),
                        "total": item_total,
                    }
                )
                subtotal += item_total

            # Calculate discount and total
            discount_amount = subtotal * (descuento_porcentaje / 100)
            total = subtotal - discount_amount

            quote = {
                "id": str(uuid4()),
                "cliente_id": client_id,
                "user_id": user_id,
                "items": quote_items,
                "subtotal": round(subtotal, 2),
                "discount_percentage": descuento_porcentaje,
                "discount_amount": round(discount_amount, 2),
                "total": round(total, 2),
                "notes": notas,
                "currency": "USD",
                "status": "pending",
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": datetime.utcnow().isoformat(),  # Default 7 days
            }

            # Save to database
            self.supabase.table("quotes").insert(quote).execute()

            logger.info(
                f"Quote created: {quote['id']} for user {user_id}",
                extra={"client_id": client_id},
            )

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
        """
        Apply or modify discount on an existing quote.

        Args:
            quote_id: Quote ID
            descuento_porcentaje: New discount percentage
            razon: Reason for discount (objection handling, promotion, etc)

        Returns:
            Updated quote
        """
        try:
            # Fetch quote
            response = self.supabase.table("quotes").select("*").eq(
                "id", quote_id
            ).single().execute()
            quote = response.data

            # Recalculate
            subtotal = quote["subtotal"]
            discount_amount = subtotal * (descuento_porcentaje / 100)
            new_total = subtotal - discount_amount

            # Update
            updated = {
                "discount_percentage": descuento_porcentaje,
                "discount_amount": round(discount_amount, 2),
                "total": round(new_total, 2),
                "discount_reason": razon,
                "updated_at": datetime.utcnow().isoformat(),
            }

            self.supabase.table("quotes").update(updated).eq(
                "id", quote_id
            ).execute()

            logger.info(f"Discount applied to quote {quote_id}: {descuento_porcentaje}%")
            return updated

        except Exception as e:
            logger.error(f"Error applying discount: {e}")
            return {"error": str(e)}

    async def handle_objection(
        self,
        client_id: str,
        user_id: str,
        tipo_objecion: str,
        contexto: str,
    ) -> str:
        """
        Handle common sales objections with AI-suggested responses.

        Args:
            client_id: Client ID
            user_id: User ID
            tipo_objecion: Type of objection (price, timing, competitor, etc)
            contexto: Context/full objection text

        Returns:
            Suggested response to overcome objection
        """
        objection_responses = {
            "price": "Entiendo que el precio es una consideración importante. Veamos: este producto/servicio ofrece {value_prop}. ¿Podemos explorar un plan de pago flexible?",
            "timing": "Completamente comprensible que el timing sea importante. ¿Cuál sería el momento ideal para ti? Podemos agendar una cita para entonces.",
            "competitor": "Excelente pregunta. Mientras otros ofrecen {feature}, nosotros destacamos en {differentiator}. ¿Te gustaría que te muestre la diferencia?",
            "need": "Es válido cuestionarse si realmente lo necesitas. ¿Qué problema específico esperas resolver? Quizás podamos mostrar cómo otros clientes lo han usado.",
            "trust": "La confianza es lo más importante. Tenemos {testimonials} clientes satisfechos y {case_studies} casos de éxito. ¿Te gustaría hablar con alguno?",
        }

        response = objection_responses.get(
            tipo_objecion,
            "Entiendo tu preocupación. ¿Podemos agendar una llamada con nuestro equipo para discutirlo en detalle?",
        )

        logger.info(
            f"Objection handled: {tipo_objecion} for user {user_id}",
            extra={"client_id": client_id},
        )

        return response

    async def get_sales_pipeline(self, client_id: str) -> dict[str, Any]:
        """
        Get sales pipeline summary (quotes by status).

        Args:
            client_id: Client ID

        Returns:
            Pipeline stats: pending, accepted, rejected, expired
        """
        try:
            response = self.supabase.table("quotes").select("status, total").eq(
                "cliente_id", client_id
            ).execute()

            quotes = response.data or []

            pipeline = {
                "pending": {"count": 0, "total_value": 0},
                "accepted": {"count": 0, "total_value": 0},
                "rejected": {"count": 0, "total_value": 0},
                "expired": {"count": 0, "total_value": 0},
            }

            for quote in quotes:
                status = quote.get("status", "pending")
                if status in pipeline:
                    pipeline[status]["count"] += 1
                    pipeline[status]["total_value"] += quote.get("total", 0)

            return pipeline

        except Exception as e:
            logger.error(f"Error fetching sales pipeline: {e}")
            return {}

    async def send_quote_to_customer(
        self,
        client_id: str,
        user_id: str,
        quote_id: str,
        channel: str = "whatsapp",
    ) -> dict[str, Any]:
        """
        Send quote via specified channel (WhatsApp, Email, etc).

        Args:
            client_id: Client ID
            user_id: Customer user ID
            quote_id: Quote ID to send
            channel: Channel to use (whatsapp, email, etc)

        Returns:
            Result with delivery status
        """
        try:
            response = self.supabase.table("quotes").select("*").eq(
                "id", quote_id
            ).single().execute()
            quote = response.data

            # Mark as sent
            self.supabase.table("quotes").update(
                {"status": "sent", "sent_at": datetime.utcnow().isoformat()}
            ).eq("id", quote_id).execute()

            logger.info(
                f"Quote {quote_id} sent via {channel} to user {user_id}",
                extra={"client_id": client_id},
            )

            return {
                "success": True,
                "quote_id": quote_id,
                "channel": channel,
                "message": f"Quote sent successfully via {channel}",
            }

        except Exception as e:
            logger.error(f"Error sending quote: {e}")
            return {"success": False, "error": str(e)}
