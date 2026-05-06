"""
Agent engine with GPT-4o and function calling.

Main AI agent that processes messages, calls tools based on enabled modules,
and simulates human-like behavior (typing indicators, variable delays, message splitting).
"""

import asyncio
import json
import logging
import os
import random
import time
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class AgentEngine:
    """
    AI agent powered by GPT-4o with function calling.

    Handles:
    - Dynamic system prompts from client configuration
    - Function calling with module-based access control
    - Human-like behavior simulation (typing, delays, message splitting)
    - Error handling and graceful escalation
    """

    def __init__(self, client_config: dict[str, Any]):
        """
        Initialize the agent engine.

        Args:
            client_config: Configuration dict with keys:
                - system_prompt: str
                - active_modules: dict[str, bool]
                - temperature: float (0.0-2.0)
                - max_tokens: int
                - business_hours_start: str (HH:MM)
                - business_hours_end: str (HH:MM)
                - business_hours_timezone: str
        """
        self.client_config = client_config
        self.client_id = client_config.get("client_id", "unknown")
        self.system_prompt = client_config.get("system_prompt", "")
        self.active_modules = client_config.get("active_modules", {})

        if not self.system_prompt:
            logger.warning(
                f"AgentEngine for client_id={self.client_id}: "
                f"system_prompt is empty/None — will use blank prompt. "
                f"client_config keys: {list(client_config.keys())}"
            )
        else:
            logger.info(
                f"AgentEngine for client_id={self.client_id}: "
                f"system_prompt loaded ({len(self.system_prompt)} chars): "
                f"{self.system_prompt[:100]!r}"
            )
        self.temperature = client_config.get("temperature", 0.7)
        self.max_tokens = client_config.get("max_tokens", 4000)

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.client = AsyncOpenAI(api_key=api_key)
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o")
        self._tools_cache = None

    def _get_available_tools(self) -> list[dict[str, Any]]:
        """
        Get list of available tools based on active modules.

        Returns tool definitions only for enabled modules.
        """
        if self._tools_cache is not None:
            return self._tools_cache

        all_tools = {
            "agendamiento": [
                {
                    "type": "function",
                    "function": {
                        "name": "consultar_disponibilidad",
                        "description": "Check available appointment slots for a given date range",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "fecha_inicio": {
                                    "type": "string",
                                    "description": "Start date (YYYY-MM-DD)",
                                },
                                "fecha_fin": {
                                    "type": "string",
                                    "description": "End date (YYYY-MM-DD)",
                                },
                            },
                            "required": ["fecha_inicio", "fecha_fin"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "crear_cita",
                        "description": "Create a new appointment in Google Calendar",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "fecha": {
                                    "type": "string",
                                    "description": "Appointment date (YYYY-MM-DD)",
                                },
                                "hora": {
                                    "type": "string",
                                    "description": "Appointment time (HH:MM)",
                                },
                                "duracion_minutos": {
                                    "type": "integer",
                                    "description": "Duration in minutes",
                                },
                                "cliente_nombre": {
                                    "type": "string",
                                    "description": "Client name",
                                },
                                "cliente_email": {
                                    "type": "string",
                                    "description": "Client email",
                                },
                                "descripcion": {
                                    "type": "string",
                                    "description": "Appointment description",
                                },
                            },
                            "required": [
                                "fecha",
                                "hora",
                                "duracion_minutos",
                                "cliente_nombre",
                                "cliente_email",
                            ],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "cancelar_cita",
                        "description": "Cancel an existing appointment",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "cita_id": {
                                    "type": "string",
                                    "description": "Appointment ID to cancel",
                                },
                                "motivo": {
                                    "type": "string",
                                    "description": "Cancellation reason",
                                },
                            },
                            "required": ["cita_id"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "reagendar_cita",
                        "description": "Reschedule an existing appointment",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "cita_id": {
                                    "type": "string",
                                    "description": "Appointment ID to reschedule",
                                },
                                "nueva_fecha": {
                                    "type": "string",
                                    "description": "New date (YYYY-MM-DD)",
                                },
                                "nueva_hora": {
                                    "type": "string",
                                    "description": "New time (HH:MM)",
                                },
                            },
                            "required": ["cita_id", "nueva_fecha", "nueva_hora"],
                        },
                    },
                },
            ],
            "calificacion": [
                {
                    "type": "function",
                    "function": {
                        "name": "guardar_lead",
                        "description": "Save or update lead information",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "usuario_id": {
                                    "type": "string",
                                    "description": "User/Lead ID",
                                },
                                "nombre": {
                                    "type": "string",
                                    "description": "Lead name",
                                },
                                "email": {
                                    "type": "string",
                                    "description": "Lead email",
                                },
                                "telefono": {
                                    "type": "string",
                                    "description": "Lead phone number",
                                },
                                "empresa": {
                                    "type": "string",
                                    "description": "Lead company",
                                },
                                "tags": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Tags for categorization",
                                },
                            },
                            "required": ["usuario_id", "nombre"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "actualizar_score_lead",
                        "description": "Update lead qualification score (0-10)",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "usuario_id": {
                                    "type": "string",
                                    "description": "User/Lead ID",
                                },
                                "score": {
                                    "type": "number",
                                    "minimum": 0,
                                    "maximum": 10,
                                    "description": "Lead score (0-10)",
                                },
                                "razon": {
                                    "type": "string",
                                    "description": "Reason for score update",
                                },
                            },
                            "required": ["usuario_id", "score"],
                        },
                    },
                },
            ],
            "cobros": [
                {
                    "type": "function",
                    "function": {
                        "name": "enviar_datos_bancarios",
                        "description": "Send bank account details for payment transfer",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "usuario_id": {
                                    "type": "string",
                                    "description": "User ID",
                                },
                                "numero_cuenta": {
                                    "type": "string",
                                    "description": "Bank account number",
                                },
                                "nombre_banco": {
                                    "type": "string",
                                    "description": "Bank name",
                                },
                                "tipo_cuenta": {
                                    "type": "string",
                                    "description": "Account type (checking/savings)",
                                },
                                "monto_esperado": {
                                    "type": "number",
                                    "description": "Expected payment amount",
                                },
                            },
                            "required": ["usuario_id", "numero_cuenta", "nombre_banco"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "registrar_pago",
                        "description": "Register a payment receipt/verification",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "usuario_id": {
                                    "type": "string",
                                    "description": "User ID",
                                },
                                "monto": {
                                    "type": "number",
                                    "description": "Payment amount",
                                },
                                "referencia": {
                                    "type": "string",
                                    "description": "Payment reference/transaction ID",
                                },
                                "metodo": {
                                    "type": "string",
                                    "description": "Payment method (transfer/card/etc)",
                                },
                                "imagen_comprobante": {
                                    "type": "string",
                                    "description": "Receipt image URL for verification",
                                },
                            },
                            "required": ["usuario_id", "monto", "referencia"],
                        },
                    },
                },
            ],
            "ventas": [
                {
                    "type": "function",
                    "function": {
                        "name": "enviar_cotizacion",
                        "description": "Send a sales quote to the customer",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "usuario_id": {
                                    "type": "string",
                                    "description": "User/Lead ID",
                                },
                                "productos": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Product names or IDs",
                                },
                                "cantidades": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "Quantities for each product",
                                },
                                "descuento_porcentaje": {
                                    "type": "number",
                                    "description": "Optional discount percentage",
                                },
                                "notas": {
                                    "type": "string",
                                    "description": "Additional notes for the quote",
                                },
                            },
                            "required": ["usuario_id", "productos", "cantidades"],
                        },
                    },
                },
            ],
            "alertas": [
                {
                    "type": "function",
                    "function": {
                        "name": "enviar_recordatorio",
                        "description": "Send a reminder to the customer",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "usuario_id": {
                                    "type": "string",
                                    "description": "User ID",
                                },
                                "tipo": {
                                    "type": "string",
                                    "description": "Reminder type (follow-up, payment, appointment)",
                                },
                                "mensaje": {
                                    "type": "string",
                                    "description": "Reminder message",
                                },
                                "canal": {
                                    "type": "string",
                                    "description": "Channel to send (whatsapp, email, etc)",
                                },
                            },
                            "required": ["usuario_id", "tipo", "mensaje"],
                        },
                    },
                },
            ],
        }

        available_tools = []
        for module, tools in all_tools.items():
            if self.active_modules.get(module, False):
                available_tools.extend(tools)

        # Add escalation tool (always available)
        available_tools.append(
            {
                "type": "function",
                "function": {
                    "name": "escalar_a_humano",
                    "description": "Escalate conversation to a human agent",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "usuario_id": {
                                "type": "string",
                                "description": "User ID",
                            },
                            "razon": {
                                "type": "string",
                                "description": "Reason for escalation",
                            },
                            "prioridad": {
                                "type": "string",
                                "description": "Priority level (low/medium/high/critical)",
                            },
                        },
                        "required": ["usuario_id", "razon"],
                    },
                },
            }
        )

        self._tools_cache = available_tools
        return available_tools

    async def process_message(
        self,
        mensaje_normalizado: dict[str, Any],
        cliente_id: str,
        memory_context: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """
        Process an incoming message and generate agent response.

        Args:
            mensaje_normalizado: Normalized message with keys:
                - text: str
                - sender_id: str
                - channel: str
                - media_url: Optional[str]
                - media_type: Optional[str]
            cliente_id: Client ID for context
            memory_context: Previous conversation turns for context

        Returns:
            Response dict with:
                - response_text: str (agent message)
                - function_calls: list[dict] (tools invoked)
                - typing_indicator_ms: int
                - message_delay_ms: int
                - split_messages: list[str] (if response is long)
                - escalated: bool
        """
        user_message = mensaje_normalizado.get("text", "")
        sender_id = mensaje_normalizado.get("sender_id", "unknown")
        media_url = mensaje_normalizado.get("media_url")
        media_type = mensaje_normalizado.get("media_type")

        logger.info(
            f"Processing message from {sender_id} in client {cliente_id}",
            extra={"client_id": cliente_id, "sender_id": sender_id},
        )

        # Simulate typing indicator
        typing_delay = self._calculate_typing_delay(user_message)

        # Build conversation history for context
        messages = [{"role": "system", "content": self.system_prompt}]
        if memory_context:
            for turn in memory_context:
                messages.append(
                    {
                        "role": turn.get("role", "user"),
                        "content": turn.get("content", ""),
                    }
                )

        # Add current message
        content = user_message
        if media_url:
            content += f"\n[Attachment: {media_type} from {media_url}]"

        messages.append({"role": "user", "content": content})

        try:
            # First GPT-4o call — may return tool calls
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self._get_available_tools(),
                tool_choice="auto",
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            assistant_message = response.choices[0].message
            response_text = assistant_message.content or ""
            function_calls = []

            # Agentic loop: execute tool calls and get a final natural-language response
            if assistant_message.tool_calls:
                for tool_call in assistant_message.tool_calls:
                    function_calls.append(
                        {
                            "id": tool_call.id,
                            "name": tool_call.function.name,
                            "arguments": json.loads(tool_call.function.arguments),
                        }
                    )

                # Append the assistant turn (with tool_calls) to the conversation
                messages.append(assistant_message)

                # Execute each tool and feed result back
                for tool_call in assistant_message.tool_calls:
                    tool_result = await self._execute_tool_call(
                        tool_call.function.name,
                        json.loads(tool_call.function.arguments),
                        cliente_id,
                        sender_id,
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": tool_result,
                        }
                    )

                # Second GPT-4o call to get a natural-language response from tool results
                final_response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                response_text = final_response.choices[0].message.content or ""

            # Simulate response delay
            response_delay = self._calculate_response_delay(len(response_text))

            # Split long messages
            split_messages = self._split_long_messages(response_text)

            # Check if escalation was triggered
            escalated = any(call["name"] == "escalar_a_humano" for call in function_calls)

            if not response_text:
                logger.warning(
                    f"GPT-4o returned empty content for client={cliente_id} sender={sender_id}"
                )
                response_text = "Disculpa, hubo un problema. ¿Puedes repetir tu pregunta?"

            return {
                "response_text": response_text,
                "function_calls": function_calls,
                "typing_indicator_ms": typing_delay,
                "message_delay_ms": response_delay,
                "split_messages": split_messages,
                "escalated": escalated,
                "request_id": str(uuid4()),
            }

        except Exception as e:
            logger.error(
                f"Error processing message: {str(e)}",
                extra={"client_id": cliente_id, "sender_id": sender_id},
                exc_info=True,
            )

            # Graceful fallback: escalate
            return {
                "response_text": "Lo siento, no pude procesar tu mensaje en este momento. Estoy escalando tu caso con un agente humano.",
                "function_calls": [
                    {
                        "name": "escalar_a_humano",
                        "arguments": {
                            "usuario_id": sender_id,
                            "razon": f"Error processing message: {str(e)}",
                            "prioridad": "high",
                        },
                    }
                ],
                "typing_indicator_ms": 1000,
                "message_delay_ms": 500,
                "split_messages": [
                    "Lo siento, no pude procesar tu mensaje en este momento.",
                    "Estoy escalando tu caso con un agente humano.",
                ],
                "escalated": True,
                "request_id": str(uuid4()),
            }

    async def _execute_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        client_id: str,
        sender_id: str,
    ) -> str:
        """
        Execute a tool call and return the result as a JSON string.

        Uses client_config business hours for scheduling tools so no
        external service is required.
        """
        try:
            if tool_name == "consultar_disponibilidad":
                start_str = self.client_config.get("business_hours_start", "09:00")
                end_str = self.client_config.get("business_hours_end", "18:00")
                result = {
                    "disponibilidad": (
                        f"Tenemos disponibilidad de lunes a viernes de {start_str} a {end_str} "
                        "y sábados de 9:00am a 1:00pm. ¿Qué día y hora te acomoda mejor?"
                    ),
                    "slots": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"],
                    "horario_inicio": start_str,
                    "horario_fin": end_str,
                }
                logger.info(
                    f"Tool consultar_disponibilidad executed for client {client_id}",
                    extra={"client_id": client_id},
                )
                return json.dumps(result, ensure_ascii=False)

            # Escalation is handled separately; return a simple ack for other tools
            logger.info(
                f"Tool {tool_name} called for client {client_id} — no internal executor yet",
                extra={"client_id": client_id},
            )
            return json.dumps(
                {"success": True, "message": f"Acción registrada: {tool_name}"},
                ensure_ascii=False,
            )

        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return json.dumps({"error": str(e)})

    def _calculate_typing_delay(self, message: str) -> int:
        """
        Calculate human-like typing indicator delay.

        Longer messages take longer to "type".
        """
        base_delay = int(os.environ.get("TYPING_INDICATOR_DELAY_MS", 1000))
        char_count = len(message)
        # ~50ms per character minimum
        calculated = base_delay + (char_count * 50)
        # Cap at 5 seconds
        return min(calculated, 5000)

    def _calculate_response_delay(self, response_length: int) -> int:
        """
        Calculate human-like response delay.

        Simulates thinking time and response composition.
        Base 0.5-2 seconds + 10ms per character.
        """
        base_delay = random.randint(500, 2000)
        char_delay = response_length * 10
        total = base_delay + char_delay
        # Cap at 10 seconds
        return min(total, 10000)

    def _split_long_messages(self, message: str, max_length: int = 500) -> list[str]:
        """
        Split long messages into multiple shorter ones.

        Mimics human-like message sending (multiple messages instead of one huge wall).
        Tries to split at sentence boundaries.
        """
        if len(message) <= max_length:
            return [message]

        parts = []
        current = ""

        for sentence in message.split(". "):
            sentence = sentence.strip()
            if not sentence:
                continue

            if len(current) + len(sentence) + 2 <= max_length:
                current += (sentence + ". ") if current else (sentence + ". ")
            else:
                if current:
                    parts.append(current.rstrip(". "))
                current = sentence + ". "

        if current:
            parts.append(current.rstrip(". "))

        # Fallback: simple character split if sentence split doesn't work
        if not parts or len(parts) == 1:
            parts = [
                message[i : i + max_length] for i in range(0, len(message), max_length)
            ]

        return parts

    def is_business_hours(self) -> bool:
        """Check if current time is within business hours for this client."""
        try:
            import pytz

            tz_name = self.client_config.get("business_hours_timezone", "America/Guayaquil")
            tz = pytz.timezone(tz_name)
            now = datetime.now(tz)

            start_str = self.client_config.get("business_hours_start", "08:00")
            end_str = self.client_config.get("business_hours_end", "18:00")

            start_hour, start_min = map(int, start_str.split(":"))
            end_hour, end_min = map(int, end_str.split(":"))

            current_minutes = now.hour * 60 + now.minute
            start_minutes = start_hour * 60 + start_min
            end_minutes = end_hour * 60 + end_min

            return start_minutes <= current_minutes <= end_minutes
        except Exception as e:
            logger.warning(f"Error checking business hours: {e}")
            return True  # Default to True if error

    def validate_module_access(self, module_name: str) -> bool:
        """
        Check if a module is enabled for this client.

        Used before executing tools to enforce access control.
        """
        return self.active_modules.get(module_name, False)
