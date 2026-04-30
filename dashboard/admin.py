"""
Admin dashboard: Business owner control panel.

Shows real-time conversations, leads, appointments, and daily metrics.
"""

import logging
import os
from datetime import datetime, timedelta

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

    if "cliente_id" not in st.session_state:
        st.session_state.cliente_id = os.getenv("CLIENT_ID", "")


def get_today_metrics(cliente_id: str):
    """Get metrics for today."""
    try:
        supabase = st.session_state.supabase
        today = datetime.utcnow().date().isoformat()

        # Messages today
        messages_response = supabase.table("mensajes").select(
            "id", count="exact"
        ).eq("cliente_id", cliente_id).gte(
            "created_at", f"{today}T00:00:00"
        ).execute()
        messages_today = messages_response.count or 0

        # Conversations started today
        conv_response = supabase.table("conversaciones").select(
            "id", count="exact"
        ).eq("cliente_id", cliente_id).gte(
            "fecha_inicio", f"{today}T00:00:00"
        ).execute()
        leads_today = conv_response.count or 0

        # Appointments today
        appts_response = supabase.table("citas").select(
            "id", count="exact"
        ).eq("cliente_id", cliente_id).gte(
            "fecha", f"{today}T00:00:00"
        ).lte("fecha", f"{today}T23:59:59").execute()
        appointments_today = appts_response.count or 0

        # Payments today
        pagos_response = supabase.table("pagos").select(
            "monto"
        ).eq("cliente_id", cliente_id).eq(
            "estado", "verificado"
        ).gte("created_at", f"{today}T00:00:00").execute()
        pagos = pagos_response.data or []
        sales_today = sum(p.get("monto", 0) for p in pagos)

        return {
            "messages": messages_today,
            "leads": leads_today,
            "sales": sales_today,
            "appointments": appointments_today,
        }

    except Exception as e:
        logger.error(f"Error fetching metrics: {e}")
        return None


def get_active_conversations(cliente_id: str, limit: int = 20):
    """Get active conversations (last activity in last 24h)."""
    try:
        supabase = st.session_state.supabase
        cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat()

        conversations = supabase.table("conversaciones").select(
            "id, usuario_id, canal, lead_state, lead_score, updated_at"
        ).eq("cliente_id", cliente_id).gte(
            "updated_at", cutoff
        ).order("updated_at", desc=True).limit(limit).execute()

        return conversations.data or []

    except Exception as e:
        logger.error(f"Error fetching conversations: {e}")
        return []


def get_hot_leads(cliente_id: str):
    """Get leads with score >= 8."""
    try:
        supabase = st.session_state.supabase

        leads = supabase.table("conversaciones").select(
            "id, usuario_id, lead_score, lead_state, updated_at"
        ).eq("cliente_id", cliente_id).gte(
            "lead_score", 8
        ).order("lead_score", desc=True).limit(20).execute()

        return leads.data or []

    except Exception as e:
        logger.error(f"Error fetching hot leads: {e}")
        return []


def get_todays_appointments(cliente_id: str):
    """Get today's appointments."""
    try:
        supabase = st.session_state.supabase
        today = datetime.utcnow().date().isoformat()

        appointments = supabase.table("citas").select(
            "id, fecha, estado, conversacion_id"
        ).eq("cliente_id", cliente_id).gte(
            "fecha", f"{today}T00:00:00"
        ).lte("fecha", f"{today}T23:59:59").order("fecha").execute()

        return appointments.data or []

    except Exception as e:
        logger.error(f"Error fetching appointments: {e}")
        return []


def get_pending_payments(cliente_id: str):
    """Get pending payment verifications."""
    try:
        supabase = st.session_state.supabase

        pagos = supabase.table("pagos").select(
            "id, monto, estado, created_at, conversacion_id"
        ).eq("cliente_id", cliente_id).eq(
            "estado", "pendiente"
        ).order("created_at", desc=True).limit(20).execute()

        return pagos.data or []

    except Exception as e:
        logger.error(f"Error fetching payments: {e}")
        return []


def take_conversation(conversation_id: str, operador_id: str):
    """Assign conversation to an operator."""
    try:
        supabase = st.session_state.supabase
        supabase.table("conversaciones").update({
            "assigned_to": operador_id,
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", conversation_id).execute()
        st.success("Conversación asignada al operador")
        st.rerun()
    except Exception as e:
        logger.error(f"Error assigning conversation: {e}")
        st.error(f"Error: {e}")


def main():
    """Main dashboard function."""
    st.set_page_config(
        page_title="Admin Dashboard",
        page_icon="📊",
        layout="wide",
    )

    st.title("📊 Business Admin Dashboard")

    init_session()

    cliente_id = st.session_state.cliente_id

    if not cliente_id:
        st.warning("No hay CLIENT_ID configurado. Configura CLIENT_ID en .streamlit/secrets.toml")
        st.info("Mostrando vista de demostración sin datos reales.")
        cliente_id = "demo"

    tab1, tab2, tab3, tab4 = st.tabs([
        "Resumen",
        "Conversaciones",
        "Leads",
        "Citas",
    ])

    # ============= TAB 1: RESUMEN =============
    with tab1:
        st.header("Resumen de hoy")

        metrics = get_today_metrics(cliente_id)

        if metrics:
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Mensajes", metrics["messages"])
            with col2:
                st.metric("Nuevas conversaciones", metrics["leads"])
            with col3:
                st.metric("Pagos verificados", f"${metrics['sales']:,.2f}")
            with col4:
                st.metric("Citas agendadas", metrics["appointments"])

        st.subheader("🔥 Leads Calientes (Score >= 8)")
        hot_leads = get_hot_leads(cliente_id)

        if hot_leads:
            leads_df = []
            for lead in hot_leads:
                leads_df.append({
                    "Usuario": lead.get("usuario_id", "")[:8],
                    "Score": lead.get("lead_score", 0),
                    "Estado": lead.get("lead_state", "N/A"),
                    "Última actividad": lead.get("updated_at", "N/A"),
                })
            st.dataframe(leads_df, use_container_width=True)
        else:
            st.info("Sin leads calientes por el momento")

        st.subheader("📅 Citas de hoy")
        appointments = get_todays_appointments(cliente_id)

        if appointments:
            appt_df = []
            for appt in appointments:
                appt_df.append({
                    "Fecha": appt.get("fecha", ""),
                    "Estado": appt.get("estado", ""),
                    "Conversación": appt.get("conversacion_id", "")[:8],
                })
            st.dataframe(appt_df, use_container_width=True)
        else:
            st.info("Sin citas agendadas para hoy")

    # ============= TAB 2: CONVERSACIONES =============
    with tab2:
        st.header("Conversaciones activas")

        filter_channel = st.selectbox(
            "Filtrar por canal",
            ["Todos", "whatsapp", "instagram", "facebook", "email"],
        )

        conversations = get_active_conversations(cliente_id)

        if conversations:
            for idx, conv in enumerate(conversations):
                if filter_channel != "Todos" and conv.get("canal") != filter_channel:
                    continue

                col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 2])

                with col1:
                    st.write(f"👤 {conv.get('usuario_id', '')[:8]}")
                with col2:
                    st.write(f"📱 {conv.get('canal', '')}")
                with col3:
                    st.write(f"💎 {conv.get('lead_score', 0)}")
                with col4:
                    st.write(f"🏷️ {conv.get('lead_state', '')}")
                with col5:
                    if st.button("Tomar", key=f"take_{idx}"):
                        operador_id = st.text_input("Tu ID de operador", key=f"op_id_{idx}")
                        if operador_id:
                            take_conversation(conv["id"], operador_id)

                st.divider()
        else:
            st.info("Sin conversaciones activas")

    # ============= TAB 3: LEADS =============
    with tab3:
        st.header("Gestión de Leads")

        try:
            supabase = st.session_state.supabase
            states = ["curioso", "prospecto", "caliente", "cliente"]
            cols = st.columns(len(states))

            for idx, state in enumerate(states):
                with cols[idx]:
                    r = supabase.table("conversaciones").select(
                        "id", count="exact"
                    ).eq("cliente_id", cliente_id).eq("lead_state", state).execute()
                    st.metric(state.capitalize(), r.count or 0)

        except Exception as e:
            st.warning(f"Error: {e}")

        st.info("Score 0-3: Curioso | 4-7: Prospecto | 8-10: Caliente | 10+: Cliente")

    # ============= TAB 4: CITAS =============
    with tab4:
        st.header("Gestión de Citas")

        next_7_days = [
            (datetime.utcnow() + timedelta(days=i)).date().isoformat()
            for i in range(7)
        ]
        selected_date = st.selectbox("Fecha", next_7_days)

        try:
            supabase = st.session_state.supabase
            appts = supabase.table("citas").select("*").eq(
                "cliente_id", cliente_id
            ).gte("fecha", f"{selected_date}T00:00:00").lte(
                "fecha", f"{selected_date}T23:59:59"
            ).order("fecha").execute()

            data = appts.data or []

            if data:
                for appt in data:
                    st.write(f"**Fecha:** {appt.get('fecha', '')}")
                    st.write(f"**Estado:** {appt.get('estado', '')}")
                    st.write(f"**Conversación:** {appt.get('conversacion_id', '')[:8]}")
                    st.divider()
            else:
                st.info("Sin citas para esta fecha")

        except Exception as e:
            st.warning(f"Error: {e}")


if __name__ == "__main__":
    main()
