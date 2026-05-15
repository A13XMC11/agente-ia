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

import pytz
from openai import AsyncOpenAI

from modulos.agendamiento import AgendamientoModule
from modulos.alertas import AlertasModule
from modulos.calificacion import CalificacionModule
from modulos.cobros import CobrosModule

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

    def __init__(self, client_config: dict[str, Any], supabase_client: Any = None, supabase_service_client: Any = None):
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
            supabase_client: Regular Supabase client for reads
            supabase_service_client: Service role Supabase client for writes with elevated permissions
        """
        self.client_config = client_config
        self.client_id = client_config.get("client_id", "unknown")
        self.system_prompt = client_config.get("system_prompt", "")
        self.active_modules = client_config.get("active_modules", {})

        logger.info(f"🟢 === AgentEngine.__init__ ===")
        logger.info(f"client_id: {self.client_id}")
        logger.info(f"active_modules: {self.active_modules}")
        logger.info(f"calificacion_enabled: {self.active_modules.get('calificacion', False)}")

        # Inject current date and time
        tz = pytz.timezone(client_config.get("business_hours_timezone", "America/Guayaquil"))
        now = datetime.now(tz)
        fecha_actual = now.strftime("%A %d de %B de %Y, %H:%M")

        _DATE_RULE = (
            f"\n\nFECHA Y HORA ACTUAL: {fecha_actual}\n\n"
            f"REGLAS DE FECHA:\n"
            f"- Hoy es {fecha_actual}\n"
            f"- Usa esta fecha para calcular 'mañana', 'este viernes', etc.\n"
            f"- Nunca inventes fechas\n"
            f"- Nunca digas que enviaste correos o tomaste acciones si no puedes hacerlo"
        )
        _OFF_TOPIC_RULE = (
            "\n\nSi el usuario hace preguntas que no tienen relación con nuestros servicios, "
            "responde amablemente que solo puedes ayudar con temas relacionados al negocio "
            "y ofrece retomar la conversación sobre los servicios."
        )
        _APPOINTMENT_RULE = (
            "\n\nREGLA DE CITAS:\n"
            "- SIEMPRE usa 'obtener_citas_usuario' PRIMERO para buscar citas existentes.\n"
            "- Luego usa el ID real (UUID) obtenido para reagendar o cancelar.\n"
            "- NUNCA uses IDs inventados o la cadena literal 'cita_id'.\n"
            "- El usuario solo puede modificar citas en estado 'confirmada'."
        )
        _AUDIO_RULE = (
            "\n\nREGLA DE AUDIOS:\n"
            "- Los mensajes de audio ya vienen transcritos a texto automáticamente\n"
            "- Nunca digas que no puedes procesar audios o que no entiendes archivos de audio\n"
            "- Simplemente responde al contenido del mensaje transcrito como si fuera texto normal\n"
            "- El usuario envió voz; tú recibiste texto — responde naturalmente"
        )
        _COBROS_RULE = (
            "\n\n🚨 REGLA CRÍTICA DE COBROS (MÁXIMA PRIORIDAD):\n"
            "INSTRUCCIÓN OBLIGATORIA: Si el usuario menciona CUALQUIERA de estos términos:\n"
            "  - transferencia, transferir, transferencias\n"
            "  - pago, pagar, pagos\n"
            "  - deposito, depositar, depósito\n"
            "  - banco, cuenta, cuenta bancaria\n"
            "  - enviar dinero, girar dinero\n"
            "\n"
            "DEBES hacer EXACTAMENTE ESTO (NO hay excepciones):\n"
            "1. PRIMERO: Invoca INMEDIATAMENTE la tool 'enviar_datos_bancarios' - SIN DEMORA\n"
            "2. NO hagas preguntas previas\n"
            "3. NO respondas con texto diciendo que enviarás los datos\n"
            "4. SOLO invoca la tool directamente\n"
            "\n"
            "Cuando recibas el resultado:\n"
            "- Copia el campo 'mensaje' tal cual (exactamente como viene, sin cambios)\n"
            "- Envía ese mensaje al usuario\n"
            "- NO reescriba, NO parafrasees, NO intentes mejorar el formato\n"
            "- El mensaje ya está listo para WhatsApp\n"
            "\n"
            "Si el usuario envía una imagen (comprobante), luego invoca 'registrar_pago'."
        )
        self.system_prompt = (self.system_prompt or "") + _DATE_RULE + _OFF_TOPIC_RULE + _APPOINTMENT_RULE + _AUDIO_RULE + _COBROS_RULE

        if not client_config.get("system_prompt"):
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

        # Log initialization status
        logger.info(
            f"AgentEngine init - supabase_service: {supabase_service_client is not None}, "
            f"supabase_client: {supabase_client is not None}"
        )

        self.supabase = supabase_client
        self.alertas = AlertasModule(supabase_client) if supabase_client else None
        self.agendamiento = AgendamientoModule(supabase_client, alertas_module=self.alertas) if supabase_client else None
        self.calificacion = CalificacionModule(supabase_service_client or supabase_client, self.alertas) if (supabase_service_client or supabase_client) else None
        self.cobros = CobrosModule(supabase_client, self.client) if supabase_client else None

        logger.info(
            f"🟢 CalificacionModule created: {self.calificacion is not None} "
            f"(client_id={self.client_id})"
        )
        if self.calificacion:
            print(f"✅ CalificacionModule READY for {self.client_id}")
            logger.info(f"🟢 CalificacionModule is NOT None - ready to use")
        else:
            print(f"❌ CalificacionModule is None for {self.client_id} - SCORING WILL BE SKIPPED")
            logger.warning(f"🔴 CalificacionModule is None - lead scoring will NOT work!")

        # Temporary storage for current message context (passed to tool calls)
        self._current_media_url = None
        self._current_media_type = None
        self._current_conversation_id = None
        self._current_phone_number_id = None

    def set_whatsapp_handler(self, handler: Any) -> None:
        """Inject WhatsApp handler for owner notifications."""
        if self.cobros:
            self.cobros.whatsapp = handler
        if self.alertas:
            self.alertas.whatsapp = handler

    def set_redis_client(self, redis_client: Any) -> None:
        """Inject Redis client for pending amount state."""
        if self.cobros:
            self.cobros.redis = redis_client

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
                        "description": "Check available appointment slots for a given date",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "cliente_id": {
                                    "type": "string",
                                    "description": "Client ID (business)",
                                },
                                "fecha": {
                                    "type": "string",
                                    "description": "Date to check (YYYY-MM-DD)",
                                },
                            },
                            "required": ["cliente_id", "fecha"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "crear_cita",
                        "description": "Create a new appointment",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "cliente_id": {
                                    "type": "string",
                                    "description": "Client ID (business)",
                                },
                                "fecha": {
                                    "type": "string",
                                    "description": "Appointment date (YYYY-MM-DD)",
                                },
                                "hora": {
                                    "type": "string",
                                    "description": "Appointment time (HH:MM)",
                                },
                                "nombre_cliente": {
                                    "type": "string",
                                    "description": "Customer name",
                                },
                                "telefono_cliente": {
                                    "type": "string",
                                    "description": "Customer phone number",
                                },
                                "servicio": {
                                    "type": "string",
                                    "description": "Service name",
                                },
                                "email_cliente": {
                                    "type": "string",
                                    "description": "Customer email (optional)",
                                },
                                "duracion_minutos": {
                                    "type": "integer",
                                    "description": "Duration in minutes (default 60)",
                                },
                            },
                            "required": [
                                "cliente_id",
                                "fecha",
                                "hora",
                                "nombre_cliente",
                                "telefono_cliente",
                                "servicio",
                            ],
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
                                "cliente_id": {
                                    "type": "string",
                                    "description": "Client ID (business)",
                                },
                                "telefono_cliente": {
                                    "type": "string",
                                    "description": "Customer phone number",
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
                            "required": ["cliente_id", "telefono_cliente", "nueva_fecha", "nueva_hora"],
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
                                "cliente_id": {
                                    "type": "string",
                                    "description": "Client ID (business)",
                                },
                                "telefono_cliente": {
                                    "type": "string",
                                    "description": "Customer phone number",
                                },
                            },
                            "required": ["cliente_id", "telefono_cliente"],
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
                        "description": "MANDATORY: You MUST invoke this tool IMMEDIATELY and ONLY when user mentions ANY of these keywords: transferencia, pagar, pago, deposito, depositar, banco, cuenta, transferir, enviar dinero. NEVER respond with text promising to send data. ALWAYS call this function first, immediately, without asking questions or waiting. The system will return formatted bank account information that you MUST send exactly as-is to the user.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "monto_esperado": {
                                    "type": "number",
                                    "description": "Expected payment amount (optional, for later validation)",
                                },
                            },
                            "required": [],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "registrar_pago",
                        "description": "Process and verify a payment receipt image. Call this when user sends a photo of their bank transfer receipt after requesting bank details. Uses the image attached to the current message.",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "required": [],
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
        print(f"\n\n{'#'*80}")
        print(f"# PROCESS_MESSAGE STARTED")
        print(f"{'#'*80}\n")
        logger.info("🔵 === PROCESS_MESSAGE STARTED ===")
        user_message = mensaje_normalizado.get("text", "")
        sender_id = mensaje_normalizado.get("sender_id", "unknown")
        media_url = mensaje_normalizado.get("media_url")
        media_type = mensaje_normalizado.get("media_type")

        logger.info(
            f"Processing message from {sender_id} in client {cliente_id}",
            extra={"client_id": cliente_id, "sender_id": sender_id},
        )
        logger.info(f"PM_START: {sender_id}")

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

        # Store media context for tool calls
        self._current_media_url = media_url
        self._current_media_type = media_type
        self._current_conversation_id = mensaje_normalizado.get("metadata", {}).get("conversation_id", "")
        self._current_phone_number_id = mensaje_normalizado.get("metadata", {}).get("phone_number_id", "")

        # Add current message with media hint for LLM
        content = user_message or ""

        # For images: add hint about payment verification
        if media_url and media_type == "image":
            if not content:
                content = "(El usuario envió una imagen)"
            content += f"\n[Imagen adjunta — si el usuario solicitó transferencia bancaria, puede ser un comprobante de pago]"
        # For transcribed audio: the text IS the transcription, don't add attachment markers
        # For other media: document, video, etc. — note the attachment but keep the text as-is
        elif media_url and media_type != "audio":
            content += f"\n[Attachment: {media_type}]"
        # For audio: never add markers; the transcribed text is the full message

        messages.append({"role": "user", "content": content})

        try:
            logger.info(f"PM_STEP_1: Received message from {sender_id}")

            # First GPT-4o call — may return tool calls
            logger.info(f"PM_STEP_2: Calling GPT-4o for {sender_id}")
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=self._get_available_tools(),
                    tool_choice="auto",
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
            except Exception as e:
                logger.error(f"SILENT_ERROR in GPT-4o_FIRST_CALL: {e}")
                import traceback
                logger.error(traceback.format_exc())
                raise

            logger.info(f"PM_STEP_3: GPT-4o call succeeded, processing response")
            assistant_message = response.choices[0].message
            response_text = assistant_message.content or ""
            function_calls = []

            # Agentic loop: execute tool calls and get a final natural-language response
            if assistant_message.tool_calls:
                logger.info(f"PM_STEP_3a: Found {len(assistant_message.tool_calls)} tool calls")
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
                    try:
                        tool_result = await self._execute_tool_call(
                            tool_call.function.name,
                            json.loads(tool_call.function.arguments),
                            cliente_id,
                            sender_id,
                        )
                        logger.info(f"PM_STEP_3b: Tool {tool_call.function.name} executed")
                    except Exception as e:
                        logger.error(f"SILENT_ERROR in TOOL_CALL {tool_call.function.name}: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        tool_result = json.dumps({"error": str(e)})

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": tool_result,
                        }
                    )

                # Second GPT-4o call to get a natural-language response from tool results
                logger.info(f"PM_STEP_3c: Calling GPT-4o for final response")
                try:
                    final_response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                    )
                    response_text = final_response.choices[0].message.content or ""
                except Exception as e:
                    logger.error(f"SILENT_ERROR in GPT-4o_SECOND_CALL: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    raise

            # Simulate response delay
            logger.info(f"PM_STEP_4: Building response dict")
            try:
                response_delay = self._calculate_response_delay(len(response_text))
                split_messages = self._split_long_messages(response_text)
                escalated = any(call["name"] == "escalar_a_humano" for call in function_calls)
            except Exception as e:
                logger.error(f"SILENT_ERROR in RESPONSE_BUILDING: {e}")
                import traceback
                logger.error(traceback.format_exc())
                raise

            if not response_text:
                logger.warning(
                    f"GPT-4o returned empty content for client={cliente_id} sender={sender_id}"
                )
                response_text = "Disculpa, hubo un problema. ¿Puedes repetir tu pregunta?"

            # Detect and send alerts (async, non-blocking)
            response_dict = {
                "response_text": response_text,
                "function_calls": function_calls,
                "typing_indicator_ms": typing_delay,
                "message_delay_ms": response_delay,
                "split_messages": split_messages,
                "escalated": escalated,
                "request_id": str(uuid4()),
            }

            # ============ LEAD SCORING (FIRST, before alerts) ============
            logger.info(f"PM_STEP_5: Before SCORING - {sender_id}")
            print(f"\n>>> SCORING CHECK: calificacion is {'INITIALIZED' if self.calificacion else 'NONE'}")
            logger.info(f"SCORING_START: sender={sender_id}, calificacion={self.calificacion is not None}")
            print(f">>> ABOUT TO CALL calcular_score_automatico for {sender_id}")
            try:
                if self.calificacion:
                    score_result = await self.calificacion.calcular_score_automatico(
                        client_id=cliente_id,
                        usuario_id=sender_id,
                        current_message=user_message,
                        prior_messages=memory_context or [],
                        current_ts=datetime.utcnow(),
                        conversation_id=self._current_conversation_id or None,
                    )
                    print(f">>> SCORING SUCCESS: result={score_result}")
                    logger.info(f"SCORING_DONE: {score_result}")
                else:
                    print(f">>> SCORING SKIPPED: no calificacion module")
                    logger.warning("SCORING_SKIP: no calificacion module")
            except Exception as e:
                import traceback
                full_trace = traceback.format_exc()
                print(f"\n{'!'*80}")
                print(f"! SCORING EXCEPTION CAUGHT")
                print(f"! Exception type: {type(e).__name__}")
                print(f"! Exception message: {str(e)}")
                print(f"! Traceback:\n{full_trace}")
                print(f"{'!'*80}\n")
                logger.error(f"SCORING_EXCEPTION: {type(e).__name__}: {e}")
                logger.error(f"SCORING_TRACEBACK:\n{full_trace}")
            # ======================================

            logger.info(f"PM_STEP_6: After SCORING - preparing alerts for {sender_id}")

            # Trigger alert detection in background
            if self.alertas:
                try:
                    logger.info(f"PM_STEP_6a: Creating alert detection task")
                    asyncio.create_task(self.alertas.detectar_y_enviar_alertas(
                        client_id=cliente_id,
                        user_message=user_message,
                        agent_response=response_dict,
                        conversation_id=self._current_conversation_id,
                        user_id=sender_id,
                        sender_id=sender_id,
                    ))
                except Exception as e:
                    logger.error(f"SILENT_ERROR in ALERT_TRIGGER: {e}")
                    import traceback
                    logger.error(traceback.format_exc())

            logger.info(f"PM_STEP_7: Returning response for {sender_id}")
            print(f"\n✓ PROCESS_MESSAGE RETURNING NORMALLY for {sender_id}")
            print(f"  Response keys: {list(response_dict.keys())}")
            print(f"  Response text: {response_dict.get('response_text', '')[:100]}...")
            return response_dict

        except Exception as e:
            import traceback
            full_trace = traceback.format_exc()

            # AGGRESSIVE LOGGING — capture everything
            print(f"\n\n{'!'*80}")
            print(f"! OUTER CATCH IN PROCESS_MESSAGE")
            print(f"! Exception type: {type(e).__name__}")
            print(f"! Exception message: {str(e)}")
            print(f"! Full traceback:\n{full_trace}")
            print(f"{'!'*80}\n")

            logger.error(
                f"FATAL_ERROR in process_message: {str(e)}",
                extra={"client_id": cliente_id, "sender_id": sender_id},
                exc_info=True,
            )
            logger.error(f"OUTER_CATCH_TYPE: {type(e).__name__}")
            logger.error(f"OUTER_CATCH_MESSAGE: {str(e)}")
            logger.error(f"FATAL_TRACEBACK:\n{full_trace}")

            # Graceful fallback: escalate
            error_response = {
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

            # Send critical alert on error
            if self.alertas:
                try:
                    asyncio.create_task(self.alertas.enviar_alerta_critica(
                        client_id=cliente_id,
                        tipo="agent_failed",
                        mensaje=f"❌ Error al procesar mensaje. El agente ha escalado el caso.\n\nError: {str(e)[:100]}",
                        conversation_id=self._current_conversation_id,
                        usuario_id=sender_id,
                    ))
                except Exception as alert_err:
                    logger.error(f"SILENT_ERROR in ERROR_ALERT: {alert_err}")
                    import traceback
                    logger.error(traceback.format_exc())

            print(f"\n✗ PROCESS_MESSAGE RETURNING ERROR RESPONSE for {sender_id}")
            print(f"  Error message: {error_response.get('response_text', '')}")
            return error_response

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

        CRITICAL: For appointment tools, always use the context client_id,
        never trust the cliente_id from GPT-4o arguments.
        """
        try:
            if tool_name == "consultar_disponibilidad":
                if not self.agendamiento:
                    return json.dumps({"error": "Módulo de agendamiento no disponible"})
                result = await self.agendamiento.consultar_disponibilidad(
                    cliente_id=client_id,
                    fecha=arguments.get("fecha", ""),
                )
                return json.dumps(result, ensure_ascii=False)

            if tool_name == "crear_cita":
                if not self.agendamiento:
                    return json.dumps({"error": "Módulo de agendamiento no disponible"})

                # Buscar lead_id del usuario para vincular con la cita
                lead_id = None
                if self.supabase:
                    try:
                        lead_response = self.supabase.table("leads").select("id").eq(
                            "cliente_id", client_id
                        ).eq("telefono", sender_id).limit(1).execute()
                        if lead_response.data:
                            lead_id = lead_response.data[0].get("id")
                    except Exception as e:
                        logger.warning(f"Error fetching lead_id for cita: {e}")

                result = await self.agendamiento.crear_cita(
                    cliente_id=client_id,
                    fecha=arguments.get("fecha", ""),
                    hora=arguments.get("hora", ""),
                    nombre_cliente=arguments.get("nombre_cliente", ""),
                    telefono_cliente=arguments.get("telefono_cliente", ""),
                    servicio=arguments.get("servicio", ""),
                    email_cliente=arguments.get("email_cliente", ""),
                    duracion_minutos=arguments.get("duracion_minutos", 60),
                    conversacion_id=self._current_conversation_id or None,
                    lead_id=lead_id,
                )
                return json.dumps(result, ensure_ascii=False)

            if tool_name == "reagendar_cita":
                if not self.agendamiento:
                    return json.dumps({"error": "Módulo de agendamiento no disponible"})
                result = await self.agendamiento.reagendar_cita(
                    cliente_id=client_id,
                    telefono_cliente=arguments.get("telefono_cliente", ""),
                    nueva_fecha=arguments.get("nueva_fecha", ""),
                    nueva_hora=arguments.get("nueva_hora", ""),
                )
                return json.dumps(result, ensure_ascii=False)

            if tool_name == "cancelar_cita":
                if not self.agendamiento:
                    return json.dumps({"error": "Módulo de agendamiento no disponible"})
                result = await self.agendamiento.cancelar_cita(
                    cliente_id=client_id,
                    telefono_cliente=arguments.get("telefono_cliente", ""),
                )
                return json.dumps(result, ensure_ascii=False)

            if tool_name == "enviar_datos_bancarios":
                if not self.cobros:
                    return json.dumps({"error": "Módulo de cobros no disponible"})
                monto = arguments.get("monto_esperado")
                result = await self.cobros.enviar_datos_bancarios(
                    client_id=client_id,
                    sender_id=sender_id,
                    monto_esperado=float(monto) if monto else None,
                )
                return json.dumps(result, ensure_ascii=False)

            if tool_name == "registrar_pago":
                if not self.cobros:
                    return json.dumps({"error": "Módulo de cobros no disponible"})
                if not self._current_media_url:
                    return json.dumps({
                        "error": "No se detectó imagen de comprobante. Por favor envía una foto del comprobante."
                    })
                result = await self.cobros.registrar_pago(
                    client_id=client_id,
                    sender_id=sender_id,
                    conversacion_id=self._current_conversation_id or "",
                    media_id=self._current_media_url,
                    phone_number_id=self._current_phone_number_id or "",
                )
                return json.dumps(result, ensure_ascii=False)

            if tool_name == "guardar_lead":
                if not self.calificacion:
                    return json.dumps({"error": "Módulo de calificación no disponible"})
                result = await self.calificacion.guardar_lead(
                    client_id=client_id,
                    usuario_id=arguments.get("usuario_id", sender_id),
                    nombre=arguments.get("nombre", ""),
                    email=arguments.get("email"),
                    telefono=arguments.get("telefono"),
                    empresa=arguments.get("empresa"),
                    tags=arguments.get("tags"),
                    conversacion_id=self._current_conversation_id or None,
                )
                return json.dumps(result, ensure_ascii=False)

            if tool_name == "actualizar_score_lead":
                if not self.calificacion:
                    return json.dumps({"error": "Módulo de calificación no disponible"})
                result = await self.calificacion.actualizar_score_lead(
                    client_id=client_id,
                    usuario_id=arguments.get("usuario_id", sender_id),
                    score=float(arguments.get("score", 0)),
                    razon=arguments.get("razon"),
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
