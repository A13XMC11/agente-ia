"""
Operator dashboard: Human advisor panel.

Shows only conversations assigned to this operator.
"""

import logging
import os
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

logger = logging.getLogger(__name__)


def init_session():
    """Initialize Streamlit session state."""
    if "supabase" not in st.session_state:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        if not supabase_url or not supabase_key:
            st.error("Missing SUPABASE_URL or SUPABASE_KEY in environment variables")
            st.stop()
        st.session_state.supabase = create_client(supabase_url, supabase_key)

    if "operador_id" not in st.session_state:
        st.session_state.operador_id = os.getenv("OPERADOR_ID", "")


def get_assigned_conversations(operador_id: str):
    """Get conversations assigned to this operator."""
    try:
        supabase = st.session_state.supabase

        conversations = supabase.table("conversaciones").select(
            "id, cliente_id, usuario_id, canal, lead_state, lead_score, updated_at"
        ).eq("assigned_to", operador_id).order(
            "updated_at", desc=True
        ).execute()

        return conversations.data or []

    except Exception as e:
        logger.error(f"Error fetching conversations: {e}")
        return []


def get_conversation_messages(conversacion_id: str, limit: int = 50):
    """Get messages in a conversation."""
    try:
        supabase = st.session_state.supabase

        messages = supabase.table("mensajes").select(
            "sender_id, sender_type, contenido, created_at, media_url"
        ).eq("conversacion_id", conversacion_id).order(
            "created_at", desc=False
        ).limit(limit).execute()

        return messages.data or []

    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        return []


def add_message_to_conversation(
    cliente_id: str,
    conversacion_id: str,
    contenido: str,
    operador_id: str,
):
    """Add operator message to conversation."""
    try:
        supabase = st.session_state.supabase

        message = {
            "id": str(__import__("uuid").uuid4()),
            "cliente_id": cliente_id,
            "conversacion_id": conversacion_id,
            "sender_id": operador_id,
            "sender_type": "operador",
            "contenido": contenido,
            "tipo": "texto",
            "estado": "enviado",
            "created_at": datetime.utcnow().isoformat(),
        }

        supabase.table("mensajes").insert(message).execute()
        return True

    except Exception as e:
        logger.error(f"Error adding message: {e}")
        return False


def release_conversation(conversacion_id: str):
    """Release conversation back to agent."""
    try:
        supabase = st.session_state.supabase

        supabase.table("conversaciones").update({
            "assigned_to": None,
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", conversacion_id).execute()

        return True

    except Exception as e:
        logger.error(f"Error releasing conversation: {e}")
        return False


def main():
    """Main dashboard function."""
    st.set_page_config(
        page_title="Operator Dashboard",
        page_icon="👨‍💼",
        layout="wide",
    )

    st.title("👨‍💼 Panel del Operador")

    init_session()

    operador_id = st.session_state.operador_id

    if not operador_id:
        st.error("No hay OPERADOR_ID configurado. Configura OPERADOR_ID en .streamlit/secrets.toml")
        return

    conversations = get_assigned_conversations(operador_id)

    col1, col2 = st.columns([1, 2])

    with col1:
        st.header(f"📋 Asignadas ({len(conversations)})")

        if conversations:
            for conv in conversations:
                button_text = f"{conv.get('usuario_id', '')[:8]} · {conv.get('canal', '')}"

                if st.button(button_text, key=f"conv_{conv['id']}", use_container_width=True):
                    st.session_state.selected_conversation = conv

            if "selected_conversation" not in st.session_state and conversations:
                st.session_state.selected_conversation = conversations[0]

            selected_conv = st.session_state.get("selected_conversation")
        else:
            st.info("Sin conversaciones asignadas")
            selected_conv = None

    with col2:
        if selected_conv:
            st.header(f"💬 {selected_conv.get('usuario_id', '')[:8]} · {selected_conv.get('canal', '')}")

            info_col1, info_col2, info_col3 = st.columns(3)

            with info_col1:
                st.metric("Lead Score", selected_conv.get("lead_score", 0))
            with info_col2:
                st.metric("Estado", selected_conv.get("lead_state", "N/A"))
            with info_col3:
                last = selected_conv.get("updated_at", "N/A")
                st.metric("Última actividad", last[-8:] if len(last) > 8 else last)

            st.divider()

            st.subheader("Historial de conversación")

            messages = get_conversation_messages(selected_conv["id"])

            if messages:
                for msg in messages:
                    sender = msg.get("sender_type", "")
                    text = msg.get("contenido", "")
                    timestamp = msg.get("created_at", "")[-8:]

                    if sender == "usuario":
                        st.write(f"👤 **Cliente** ({timestamp})")
                    elif sender == "agente":
                        st.write(f"🤖 **Agente** ({timestamp})")
                    else:
                        st.write(f"👨‍💼 **Operador** ({timestamp})")

                    st.write(text)
                    st.divider()
            else:
                st.info("Sin mensajes en esta conversación")

            st.subheader("Enviar mensaje")

            message_text = st.text_area(
                "Tu respuesta",
                placeholder="Escribe tu respuesta aquí...",
                height=100,
            )

            col_a, col_b, col_c = st.columns([2, 1, 1])

            with col_b:
                if st.button("Enviar", use_container_width=True):
                    if message_text.strip():
                        if add_message_to_conversation(
                            selected_conv.get("cliente_id", ""),
                            selected_conv["id"],
                            message_text,
                            operador_id,
                        ):
                            st.success("Mensaje enviado")
                            st.rerun()
                        else:
                            st.error("Error al enviar el mensaje")
                    else:
                        st.warning("El mensaje no puede estar vacío")

            with col_c:
                if st.button("Liberar", use_container_width=True):
                    if release_conversation(selected_conv["id"]):
                        st.success("Conversación devuelta al agente")
                        st.rerun()
                    else:
                        st.error("Error al liberar la conversación")
        else:
            st.info("Selecciona una conversación para comenzar")


if __name__ == "__main__":
    main()
