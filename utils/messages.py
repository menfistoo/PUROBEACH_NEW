"""
Centralized Spanish UI messages.
All user-facing text in Spanish for consistency.
"""

MESSAGES = {
    # Success messages
    'login_success': 'Bienvenido {name}',
    'logout_success': 'Sesión cerrada correctamente',
    'reservation_created': 'Reserva creada exitosamente',
    'reservation_updated': 'Reserva actualizada correctamente',
    'reservation_deleted': 'Reserva eliminada',
    'customer_created': 'Cliente creado exitosamente',
    'customer_updated': 'Cliente actualizado correctamente',
    'customer_deleted': 'Cliente eliminado',
    'user_created': 'Usuario creado exitosamente',
    'user_updated': 'Usuario actualizado correctamente',
    'user_deleted': 'Usuario eliminado',
    'furniture_created': 'Mobiliario creado exitosamente',
    'furniture_updated': 'Mobiliario actualizado correctamente',
    'furniture_deleted': 'Mobiliario eliminado',
    'zone_created': 'Zona creada exitosamente',
    'zone_updated': 'Zona actualizada correctamente',
    'zone_deleted': 'Zona eliminada',
    'merge_success': 'Clientes fusionados exitosamente',
    'import_success': 'Importación completada: {imported} registros importados',
    'profile_updated': 'Perfil actualizado correctamente',
    'password_updated': 'Contraseña actualizada correctamente',

    # Error messages
    'invalid_credentials': 'Usuario o contraseña incorrectos',
    'permission_denied': 'No tiene permisos para esta acción',
    'customer_required': 'El cliente es requerido',
    'date_required': 'La fecha es requerida',
    'invalid_date_range': 'La fecha de fin debe ser posterior a la fecha de inicio',
    'furniture_unavailable': 'El mobiliario no está disponible para las fechas seleccionadas',
    'furniture_has_reservations': 'No se puede eliminar mobiliario con reservas activas',
    'zone_has_furniture': 'No se puede eliminar zona con mobiliario activo',
    'customer_has_reservations': 'No se puede eliminar cliente con reservas activas',
    'invalid_capacity': 'Capacidad insuficiente para el número de personas',
    'duplicate_customer': 'Ya existe un cliente con estos datos',
    'room_required_interno': 'El número de habitación es requerido para clientes internos',
    'username_exists': 'El nombre de usuario ya existe',
    'email_exists': 'El correo electrónico ya existe',
    'invalid_email': 'Formato de correo electrónico inválido',
    'invalid_phone': 'Formato de teléfono inválido',
    'password_mismatch': 'Las contraseñas no coinciden',
    'password_too_short': 'La contraseña debe tener al menos 6 caracteres',
    'cannot_delete_self': 'No puede eliminarse a sí mismo',
    'cannot_delete_last_admin': 'No puede eliminar el último administrador',
    'invalid_file_type': 'Tipo de archivo no permitido',
    'file_too_large': 'El archivo es demasiado grande',

    # Validation messages
    'field_required': 'Este campo es requerido',
    'invalid_value': 'Valor inválido',

    # Info messages
    'no_results': 'Sin resultados',
    'loading': 'Cargando...',
    'confirm_delete': '¿Está seguro de eliminar este registro?',
    'confirm_merge': '¿Está seguro de fusionar estos clientes?',

    # Button/Action labels
    'save': 'Guardar',
    'cancel': 'Cancelar',
    'edit': 'Editar',
    'delete': 'Eliminar',
    'search': 'Buscar',
    'filter': 'Filtrar',
    'export': 'Exportar',
    'import': 'Importar',
    'create': 'Crear',
    'update': 'Actualizar',
    'confirm': 'Confirmar',
    'close': 'Cerrar',
    'back': 'Volver',
    'next': 'Siguiente',
    'previous': 'Anterior',
    'submit': 'Enviar',

    # Module titles
    'beach_map': 'Mapa de Beach Club',
    'reservations': 'Gestión de Reservas',
    'customers': 'Gestión de Clientes',
    'users': 'Gestión de Usuarios',
    'roles': 'Gestión de Roles',
    'furniture': 'Gestión de Mobiliario',
    'zones': 'Gestión de Zonas',
    'config': 'Configuración',
    'reports': 'Informes',
    'hotel_guests': 'Huéspedes de Hotel',
    'dashboard': 'Panel de Control',

    # Table headers
    'name': 'Nombre',
    'email': 'Correo Electrónico',
    'phone': 'Teléfono',
    'room': 'Habitación',
    'date': 'Fecha',
    'start_date': 'Fecha Inicio',
    'end_date': 'Fecha Fin',
    'state': 'Estado',
    'customer': 'Cliente',
    'furniture': 'Mobiliario',
    'zone': 'Zona',
    'capacity': 'Capacidad',
    'people': 'Personas',
    'actions': 'Acciones',
    'created': 'Creado',
    'updated': 'Actualizado',

    # Customer types
    'customer_interno': 'Cliente Interno',
    'customer_externo': 'Cliente Externo',

    # Reservation states
    'state_pendiente': 'Pendiente',
    'state_confirmada': 'Confirmada',
    'state_checkin': 'Check-in',
    'state_activa': 'Activa',
    'state_completada': 'Completada',
    'state_cancelada': 'Cancelada',
    'state_noshow': 'No-Show',
    'state_liberada': 'Liberada',
}


def get_message(key: str, **kwargs) -> str:
    """
    Get message with optional formatting.

    Args:
        key: Message key
        **kwargs: Format parameters

    Returns:
        Formatted message or key if not found
    """
    message = MESSAGES.get(key, key)
    if kwargs:
        return message.format(**kwargs)
    return message
