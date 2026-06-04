"""Global application state — service instances shared across routers."""
from typing import Any, Optional

message_router: Optional[Any] = None
auth_manager: Optional[Any] = None
rate_limiter: Optional[Any] = None
supabase_client: Optional[Any] = None
supabase_service_client: Optional[Any] = None
normalizer: Optional[Any] = None
buffer: Optional[Any] = None
memory: Optional[Any] = None
validator: Optional[Any] = None
whatsapp_handler: Optional[Any] = None
instagram_handler: Optional[Any] = None
facebook_handler: Optional[Any] = None
email_handler: Optional[Any] = None
alertas_module: Optional[Any] = None
seguimiento_module: Optional[Any] = None
catalog_sync_module: Optional[Any] = None
campanas_module: Optional[Any] = None
scheduler: Optional[Any] = None
payphone_billing: Optional[Any] = None
