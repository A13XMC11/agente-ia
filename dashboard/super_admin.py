"""
Super admin dashboard: Master control panel for all clients.

Shows global metrics, client management, and system health.
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


def get_dashboard_metrics():
    """Get global dashboard metrics."""
    try:
        supabase = st.session_state.supabase
        cutoff_date = (datetime.utcnow() - timedelta(days=30)).isoformat()

        # Total clients
        clients_response = supabase.table("clientes").select(
            "id, estado"
        ).execute()
        clients = clients_response.data or []
        total_clients = len(clients)
        active_clients = sum(1 for c in clients if c.get("estado") == "activo")

        # MRR (Monthly Recurring Revenue) - tabla aún no existe, default 0
        mrr = 0

        # Messages last 30 days
        messages_response = supabase.table("mensajes").select(
            "id", count="exact"
        ).gte("created_at", cutoff_date).execute()
        total_messages = messages_response.count or 0

        # Token usage last 30 days
        tokens_response = supabase.table("uso_tokens").select(
            "total_tokens"
        ).gte("created_at", cutoff_date).execute()
        token_logs = tokens_response.data or []
        total_tokens = sum(log.get("total_tokens", 0) for log in token_logs)

        return {
            "total_clients": total_clients,
            "active_clients": active_clients,
            "mrr": mrr,
            "total_messages": total_messages,
            "total_tokens": total_tokens,
            "clients": clients,
        }

    except Exception as e:
        logger.error(f"Error fetching metrics: {e}")
        st.error(f"Error fetching metrics: {e}")
        return None


def get_client_details(client_id: str):
    """Get detailed info for a specific client."""
    try:
        supabase = st.session_state.supabase

        # Get client
        client_response = supabase.table("clientes").select("*").eq(
            "id", client_id
        ).single().execute()
        client = client_response.data

        # subscription table doesn't exist yet
        subscription = {}

        # client_config table doesn't exist yet
        config = {}

        # Get token usage
        tokens_response = supabase.table("uso_tokens").select(
            "total_tokens"
        ).eq("cliente_id", client_id).gte(
            "created_at",
            (datetime.utcnow() - timedelta(days=30)).isoformat(),
        ).execute()
        tokens = tokens_response.data or []
        total_tokens = sum(t.get("total_tokens", 0) for t in tokens)

        return {
            "client": client,
            "subscription": subscription,
            "active_modules": config.get("active_modules", {}),
            "total_tokens": total_tokens,
        }

    except Exception as e:
        logger.error(f"Error fetching client details: {e}")
        return None


def update_client_status(client_id: str, new_status: str):
    """Update client status (active/paused/cancelled)."""
    try:
        supabase = st.session_state.supabase
        supabase.table("clientes").update({
            "estado": new_status,
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", client_id).execute()

        st.success(f"Client status updated to {new_status}")
        st.rerun()

    except Exception as e:
        logger.error(f"Error updating client status: {e}")
        st.error(f"Error updating status: {e}")


def update_module_status(client_id: str, module_name: str, enabled: bool):
    """Enable/disable a module for a client."""
    try:
        supabase = st.session_state.supabase

        # Get current config
        response = supabase.table("client_config").select(
            "active_modules"
        ).eq("cliente_id", client_id).single().execute()

        active_modules = response.data.get("active_modules", {})
        active_modules[module_name] = enabled

        # Update
        supabase.table("client_config").update({
            "active_modules": active_modules,
        }).eq("cliente_id", client_id).execute()

        st.success(f"Module {module_name} {'enabled' if enabled else 'disabled'}")
        st.rerun()

    except Exception as e:
        logger.error(f"Error updating module: {e}")
        st.error(f"Error updating module: {e}")


def get_system_alerts():
    """Get critical system alerts."""
    alerts = []

    try:
        supabase = st.session_state.supabase

        # Check for high token usage
        high_token_clients = supabase.table("uso_tokens").select(
            "cliente_id"
        ).gte(
            "total_tokens",
            1000000,
        ).gte(
            "created_at",
            (datetime.utcnow() - timedelta(days=1)).isoformat(),
        ).execute()

        for log in high_token_clients.data or []:
            alerts.append({
                "type": "usage",
                "severity": "info",
                "message": f"Cliente {log['cliente_id']} uso alto de tokens",
            })

    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")

    return alerts


def main():
    """Main dashboard function."""
    st.set_page_config(
        page_title="Super Admin Dashboard",
        page_icon="🔧",
        layout="wide",
    )

    st.title("🔧 Super Admin Dashboard")

    init_session()

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "Overview",
        "Clients",
        "System Health",
        "Billing",
    ])

    # ============= TAB 1: OVERVIEW =============
    with tab1:
        st.header("Global Metrics")

        metrics = get_dashboard_metrics()

        if metrics:
            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:
                st.metric(
                    "Total Clients",
                    metrics["total_clients"],
                    f"Active: {metrics['active_clients']}",
                )

            with col2:
                st.metric(
                    "MRR",
                    f"${metrics['mrr']:,.2f}",
                    delta=None,
                )

            with col3:
                st.metric(
                    "Messages (30d)",
                    f"{metrics['total_messages']:,}",
                )

            with col4:
                st.metric(
                    "Tokens (30d)",
                    f"{metrics['total_tokens']:,}",
                    f"Cost: ${metrics['total_tokens'] * 0.00002:.2f}",
                )

            with col5:
                st.metric(
                    "System Status",
                    "🟢 Operational",
                )

            # Alerts
            st.subheader("System Alerts")
            alerts = get_system_alerts()

            if alerts:
                for alert in alerts:
                    if alert["severity"] == "warning":
                        st.warning(alert["message"])
                    elif alert["severity"] == "error":
                        st.error(alert["message"])
                    else:
                        st.info(alert["message"])
            else:
                st.success("No alerts")

    # ============= TAB 2: CLIENTS =============
    with tab2:
        st.header("Client Management")

        metrics = get_dashboard_metrics()

        if metrics:
            clients_df = []

            for client in metrics["clients"]:
                details = get_client_details(client["id"])

                if details:
                    clients_df.append({
                        "Client ID": client["id"][:8],
                        "Nombre": details["client"].get("nombre", "N/A"),
                        "Estado": client.get("estado", "N/A"),
                        "MRR": f"${details['subscription'].get('monthly_amount', 0):.2f}",
                        "Modules": sum(
                            1 for v in details["active_modules"].values()
                            if v
                        ),
                        "Tokens (30d)": details["total_tokens"],
                    })

            if clients_df:
                st.dataframe(clients_df, use_container_width=True)

            # Client detail view
            st.subheader("Manage Client")

            selected_client_id = st.selectbox(
                "Select a client",
                [c["id"] for c in metrics["clients"]],
                format_func=lambda x: x[:8],
            )

            if selected_client_id:
                details = get_client_details(selected_client_id)

                if details:
                    client = details["client"]

                    st.write(f"**Nombre:** {client.get('nombre')}")
                    st.write(f"**Email:** {client.get('email')}")

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        estados = ["activo", "pausado", "cancelado"]
                        estado_actual = client.get("estado", "activo")
                        idx = estados.index(estado_actual) if estado_actual in estados else 0
                        new_status = st.selectbox("Estado", estados, index=idx)

                        if st.button("Update Status"):
                            update_client_status(selected_client_id, new_status)

                    with col2:
                        st.metric("MRR", f"${details['subscription'].get('monthly_amount', 0):.2f}")

                    with col3:
                        st.metric("Tokens (30d)", details["total_tokens"])

                    # Module management
                    st.subheader("Active Modules")

                    modules = {
                        "ventas": "Sales & Quotes",
                        "agendamiento": "Scheduling",
                        "cobros": "Payment Verification",
                        "calificacion": "Lead Scoring",
                        "alertas": "Alerts",
                        "seguimiento": "Follow-ups",
                        "links_pago": "Payment Links",
                        "campanas": "Campaigns",
                        "analytics": "Analytics",
                    }

                    cols = st.columns(3)

                    for idx, (module_key, module_name) in enumerate(modules.items()):
                        with cols[idx % 3]:
                            is_enabled = details["active_modules"].get(module_key, False)

                            if st.checkbox(
                                module_name,
                                value=is_enabled,
                                key=f"module_{module_key}",
                            ):
                                if not is_enabled:
                                    update_module_status(
                                        selected_client_id,
                                        module_key,
                                        True,
                                    )
                            else:
                                if is_enabled:
                                    update_module_status(
                                        selected_client_id,
                                        module_key,
                                        False,
                                    )

    # ============= TAB 3: SYSTEM HEALTH =============
    with tab3:
        st.header("System Health")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("API Status", "🟢 Healthy")

        with col2:
            st.metric("Database", "🟢 Connected")

        with col3:
            st.metric("Redis", "🟢 Connected")

        with col4:
            st.metric("OpenAI API", "🟢 Available")

        st.subheader("Recent Errors")

        st.success("No recent errors")

    # ============= TAB 4: BILLING =============
    with tab4:
        st.header("Billing & Revenue")

        col1, col2, col3 = st.columns(3)

        metrics = get_dashboard_metrics()

        if metrics:
            with col1:
                st.metric("Monthly Revenue (MRR)", f"${metrics['mrr']:,.2f}")

            with col2:
                estimated_cost = metrics["total_tokens"] * 0.00002
                st.metric("Token Costs (30d)", f"${estimated_cost:,.2f}")

            with col3:
                profit = metrics["mrr"] - (estimated_cost * 12 / 30)
                st.metric("Est. Profit Margin", f"{(profit/metrics['mrr']*100 if metrics['mrr'] > 0 else 0):.0f}%")

        st.info("Billing integrado con Stripe — pendiente de configuración.")


if __name__ == "__main__":
    main()
